# Quick check behind 0017, kept as run. Usage: PYTHONPATH=. python scripts/network_check_screen.py data/forecast/network
# Read-only screen on 2025. Does a network signal add to final_clean's saved forecasts?
# Stacking check, not a refit. Never reads 2026.
import duckdb, numpy as np, pandas as pd, pickle, sys
from sklearn.linear_model import LogisticRegression
S=sys.argv[1]; c=duckdb.connect(); d=pickle.load(open(S+'/comm.pkl','rb')); big=d['big']; ix={a:i for i,a in enumerate(big)}
print('airports with 20k+ departures 2023-24:',c.sql("select count(*) from (select origin from read_parquet(['data/flights/2023_*.parquet','data/flights/2024_*.parquet']) group by 1 having count(*)>=20000)").fetchall()[0][0], '; at 19k:',c.sql("select count(*) from (select origin from read_parquet(['data/flights/2023_*.parquet','data/flights/2024_*.parquet']) group by 1 having count(*)>=19000)").fetchall()[0][0],'; at 21k:',c.sql("select count(*) from (select origin from read_parquet(['data/flights/2023_*.parquet','data/flights/2024_*.parquet']) group by 1 having count(*)>=21000)").fetchall()[0][0])
files=["data/flights/2024_12.parquet"]+[f"data/flights/2025_{m:02d}.parquet" for m in range(1,13)]
ev=c.execute("""select origin a, dep_known_at t, (cancelled or dep_delay_min>=15)::int l from read_parquet(?) where dep_known_at is not null""",[files]).df()
ev=ev[ev.a.isin(big)]
T0=pd.Timestamp('2024-12-01'); b=((ev.t-T0)/pd.Timedelta(minutes=15)).astype(int).to_numpy(); nb=b.max()+2
ai=ev.a.map(ix).to_numpy(); N=np.zeros((nb,len(big))); L=np.zeros((nb,len(big)))
np.add.at(N,(b,ai),1); np.add.at(L,(b,ai),ev.l.to_numpy())
cN=np.vstack([np.zeros(len(big)),N.cumsum(0)]); cL=np.vstack([np.zeros(len(big)),L.cumsum(0)])
def win(bins): # last 2 h of complete 15-min bins strictly before as_of's bin
    lo=np.maximum(bins-8,0); return cN[bins]-cN[lo], cL[bins]-cL[lo]
# weights
co=d['P']['co']; comm=np.zeros(len(big),int)
for i,cm in enumerate(co):
    for a in cm: comm[ix[a]]=i
M=np.array([[comm[i]==comm[j] and i!=j for j in range(len(big))] for i in range(len(big))],float)  # same community, not self
r=c.execute("select origin a,dest b,count(*) n from read_parquet(['data/flights/2023_*.parquet','data/flights/2024_*.parquet']) group by 1,2").df()
R=np.zeros((len(big),len(big)))
for x in r.itertuples():
    if x.a in ix and x.b in ix: R[ix[x.a],ix[x.b]]+=x.n; R[ix[x.b],ix[x.a]]+=x.n
Allb=np.ones_like(M)-np.eye(len(big))
def signal(bins,node,W,ss={}):
    n,l=win(bins); W_=W[node]
    A=(n*W_).sum(1); B=(l*W_).sum(1)
    return np.where(A>=20,B/np.maximum(A,1),np.nan)
cur=c.execute("""select c.flight_id,c.lead_h,c.origin,c.dest,c.outcome,r.as_of_utc,r.flight_date,
  1-c.p_early-c.p_0_15 p, c.p_60_75+c.p_75_90+c.p_90_105+c.p_105_120+c.p_120_135+c.p_135_150+c.p_150_165+c.p_165_180+c.p_180p+c.p_cancelled+c.p_diverted miss60
  from read_parquet('data/forecast/alternatives/replay_final_clean/current.parquet') c
  join read_parquet('data/forecast/rows.parquet') r using(flight_id,lead_h)""").df()
print('outcome values',cur.outcome.value_counts().head(4).to_dict(),' rows',len(cur))
assert cur.flight_date.astype(str).str[:4].eq('2025').all()
keep=cur.origin.isin(big)&cur.dest.isin(big); print('share of 2025 forecasts on these airports',round(keep.mean(),3)); cur=cur[keep].reset_index(drop=True)
cur['y']=(~cur.outcome.isin(['early','0-15'])).astype(int)
print('observed late',round(cur.y.mean(),4),'mean predicted',round(cur.p.mean(),4))
def add(df):
    b=((df.as_of_utc-T0)/pd.Timedelta(minutes=15)).astype(int).to_numpy()
    o=df.origin.map(ix).to_numpy(); de=df.dest.map(ix).to_numpy(); X={}
    X['o_comm']=signal(b,o,M); X['d_comm']=signal(b,de,M)
    X['o_route']=signal(b,o,R); X['d_route']=signal(b,de,R)
    X['national']=signal(b,o,Allb)
    return pd.DataFrame(X)
F=add(cur)
days=pd.to_datetime(cur.flight_date).dt.dayofyear.to_numpy(); rng=np.random.default_rng(0); u=rng.random(367); tr=u[days]<.5
hr=cur.as_of_utc.dt.hour.to_numpy()
print('blank share', F.isna().mean().round(3).to_dict())
for k in F:
    typ=pd.Series(F[k].values[tr]).groupby(hr[tr]).mean(); F[k]=F[k]-pd.Series(hr).map(typ).values
lg=np.log(np.clip(cur.p,1e-4,1-1e-4)/(1-np.clip(cur.p,1e-4,1-1e-4))).to_numpy()
def run(cols,mask):
    Z=np.column_stack([lg]+[F[k].fillna(F[k].mean()).to_numpy() for k in cols]); mm=mask
    m=LogisticRegression(C=1e4,max_iter=300).fit(Z[mm&tr],cur.y[mm&tr]); return m.predict_proba(Z)[:,1]
res=[]
for lead in (2,6,24,None):
    mask=np.ones(len(cur),bool) if lead is None else (cur.lead_h==lead).to_numpy()
    base=run([],mask)
    te=mask&~tr; y=cur.y.to_numpy()
    bb=(base-y)**2; raw=(cur.p.to_numpy()-y)**2
    print(f"\nlead {lead}: test forecasts {te.sum():,}; late Brier saved {raw[te].mean():.5f}; recalibrated only {bb[te].mean():.5f}")
    for name,cols in (('national, no graph',['national']),('routes, 1 hop',['o_route','d_route']),('community',['o_comm','d_comm']),('community+routes+national',['o_comm','d_comm','o_route','d_route','national'])):
        p=run(cols,mask); dd=(p-y)**2-bb
        s=pd.DataFrame({'d':days[te],'x':dd[te]}).groupby('d').x.agg(['sum','count'])
        bo=[]; k=len(s); 
        for _ in range(500):
            i=rng.integers(0,k,k); bo.append(s['sum'].values[i].sum()/s['count'].values[i].sum())
        print(f"  {name:28s} change {dd[te].mean():+.5f} ({np.percentile(bo,2.5):+.5f} to {np.percentile(bo,97.5):+.5f})")
typ_o=pd.Series(signal(((cur.as_of_utc-T0)/pd.Timedelta(minutes=15)).astype(int).to_numpy(),cur.origin.map(ix).to_numpy(),M)[tr]).groupby(hr[tr]).mean()
from sklearn.ensemble import HistGradientBoostingClassifier as H
y=cur.y.to_numpy(); ld=cur.lead_h.to_numpy(); si=np.random.default_rng(1).random(len(cur))<.5
base=np.column_stack([lg,ld,hr]); te=~tr
def hgb(Z):
    m=H(max_iter=150,learning_rate=.05,max_leaf_nodes=31,random_state=0).fit(Z[tr&si],y[tr&si]); return m.predict_proba(Z)[:,1]
pb=hgb(base); bb=(pb-y)**2
print('\nnon-linear check, all leads, test',te.sum(),'; base Brier',round(bb[te].mean(),5),'saved',round(((cur.p.to_numpy()-y)**2)[te].mean(),5))
for name,cols in (('national',['national']),('routes',['o_route','d_route']),('community',['o_comm','d_comm'])):
    p=hgb(np.column_stack([base]+[F[k].to_numpy() for k in cols])); dd=(p-y)**2-bb
    s=pd.DataFrame({'d':days[te],'x':dd[te]}).groupby('d').x.agg(['sum','count']); bo=[]; k=len(s)
    for _ in range(500):
        i=rng.integers(0,k,k); bo.append(s['sum'].values[i].sum()/s['count'].values[i].sum())
    print(f"  {name:12s} change {dd[te].mean():+.5f} ({np.percentile(bo,2.5):+.5f} to {np.percentile(bo,97.5):+.5f})")
    if name=='community':
        hi=te&(F.o_comm.fillna(-9).to_numpy()>=np.nanquantile(F.o_comm,.95)); print('   on the most disrupted 5% of moments: n',hi.sum(),'change',round(dd[hi].mean(),5),'base Brier',round(bb[hi].mean(),5))
# Shared disruption: are alternatives over-promised when the region is disrupted?
alt=c.execute("""select p.flight_id,p.lead_h,p.alt,p.as_of_utc,a.outcome,1-a.p_early-a.p_0_15 p_alt,
   r.origin,r.dest,ar.origin ao,ar.dest ad
  from read_parquet('data/forecast/alternatives/replay_final_clean/pairs.parquet') p
  join read_parquet('data/forecast/alternatives/replay_final_clean/alt_forecasts.parquet') a on a.alt=p.alt and a.alt_lead=p.alt_lead
  join read_parquet('data/forecast/rows.parquet') r on r.flight_id=p.flight_id and r.lead_h=p.lead_h
  join (select distinct flight_id,origin,dest from read_parquet('data/forecast/alternatives/replay_final_clean/alt_rows.parquet')) ar on ar.flight_id=p.alt""").df()
print('\npairs',len(alt),'same route share',round(((alt.origin==alt.ao)&(alt.dest==alt.ad)).mean(),4))
alt=alt[alt.origin.isin(big)&alt.dest.isin(big)].reset_index(drop=True)
alt['y']=(~alt.outcome.isin(['early','0-15'])).astype(int)
b=((alt.as_of_utc-T0)/pd.Timedelta(minutes=15)).astype(int).to_numpy(); s=signal(b,alt.origin.map(ix).to_numpy(),M); alt['s']=s
alt['hr']=alt.as_of_utc.dt.hour; alt=alt.dropna(subset=['s']); alt['s']=alt.s-alt.hr.map(typ_o); q=alt.s.quantile([.5,.9,.99]).values; print('community signal quantiles .5/.9/.99',q.round(3))
alt['band']=pd.cut(alt.s,[-1,q[0],q[1],q[2],2],labels=['bottom half','50-90%','90-99%','top 1%'])
print(alt.groupby('band',observed=True).agg(pairs=('y','size'),pred=('p_alt','mean'),true=('y','mean')).assign(gap=lambda t:t.true-t.pred).round(4).to_string())
cur['s']=F.o_comm; x=cur.dropna(subset=['s']).copy(); x['band']=pd.cut(x.s,[-1,q[0],q[1],q[2],2],labels=['bottom half','50-90%','90-99%','top 1%'])
print('\ncurrent flights, same bands'); print(x.groupby('band',observed=True).agg(n=('y','size'),pred=('p','mean'),true=('y','mean')).assign(gap=lambda t:t.true-t.pred).round(4).to_string())
