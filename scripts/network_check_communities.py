# Quick check behind 0017, kept as run. Usage: PYTHONPATH=. python scripts/network_check_communities.py data/forecast/network
# Read-only probe. Communities from 2023-24 only. Writes nothing to the repo. Never reads 2026.
import duckdb, numpy as np, pandas as pd, networkx as nx, sys, pickle
from networkx.algorithms.community import louvain_communities, modularity
from sklearn.metrics import adjusted_rand_score as ari
S=sys.argv[1]; c=duckdb.connect()
def src(y): return f"read_parquet('data/flights/{y}_*.parquet')"
MIN=20000  # about 27 flights/day over two years
big=[r[0] for r in c.sql(f"select origin from read_parquet(['data/flights/2023_*.parquet','data/flights/2024_*.parquet']) group by 1 having count(*)>={MIN}").fetchall()]
print('airports kept',len(big))
def labels(comms,nodes):
    m={n:i for i,cm in enumerate(comms) for n in cm}; return [m[n] for n in nodes]
def route_graph(y):
    d=c.sql(f"select origin a,dest b,count(*) n from {src(y)} group by 1,2").df()
    d=d[d.a.isin(big)&d.b.isin(big)]; G=nx.Graph()
    G.add_nodes_from(big)
    for r in d.itertuples():
        w=G[r.a][r.b]['weight']+r.n if G.has_edge(r.a,r.b) else r.n
        G.add_edge(r.a,r.b,weight=w)
    return G
def panel(y):
    # share of departures 15+ late or cancelled, per airport per 3-hour block, minus that airport's usual for hour and month
    d=c.sql(f"""select origin a, time_bucket(interval 3 hour, sched_dep_utc) t,
        avg(case when cancelled or dep_delay_min>=15 then 1.0 else 0.0 end) s, count(*) n from {src(y)} group by 1,2""").df()
    d=d[d.a.isin(big)&(d.n>=3)]
    d['h']=d.t.dt.hour; d['m']=d.t.dt.month
    d['x']=d.s-d.groupby(['a','h','m']).s.transform('mean')
    return d.pivot(index='t',columns='a',values='x')
def co_graph(y,top=8):
    C=panel(y).corr(min_periods=300).reindex(index=big,columns=big); A=C.values.copy(); np.fill_diagonal(A,np.nan)
    G=nx.Graph(); G.add_nodes_from(big)
    for i,a in enumerate(big):
        row=A[i]; 
        if np.all(np.isnan(row)): continue
        for j in np.argsort(-np.nan_to_num(row,nan=-9))[:top]:
            if row[j]>0: G.add_edge(a,big[j],weight=float(row[j]))
    return G,C
out={}
for name,mk in (('route',route_graph),('co',lambda y:co_graph(y)[0])):
    G3,G4=mk(2023),mk(2024)
    runs=[louvain_communities(G3,weight='weight',seed=s) for s in range(10)]
    r4=louvain_communities(G4,weight='weight',seed=0)
    L=[labels(x,big) for x in runs]
    seedari=np.mean([ari(L[0],l) for l in L[1:]])
    yrari=ari(L[0],labels(r4,big))
    print(f"\n== {name}: communities {len(runs[0])} (2023), {len(r4)} (2024); modularity {modularity(G3,runs[0],weight='weight'):.3f}; same-partition score across seeds {seedari:.2f}; 2023 vs 2024 {yrari:.2f}")
    # final partition on both years
    Gb=nx.Graph(); Gb.add_nodes_from(big)
    for G in (G3,G4):
        for a,b,d in G.edges(data=True):
            w=d['weight']; 
            if Gb.has_edge(a,b): Gb[a][b]['weight']+=w
            else: Gb.add_edge(a,b,weight=w)
    P=louvain_communities(Gb,weight='weight',seed=0); P=sorted(P,key=len,reverse=True); out[name]=P
    vol=c.sql("select origin a,count(*) n from read_parquet(['data/flights/2023_*.parquet','data/flights/2024_*.parquet']) group by 1").df().set_index('a').n
    for i,cm in enumerate(P):
        print(f"  {i} n={len(cm):3d}:",' '.join(sorted(cm,key=lambda a:-vol[a])[:16]))
pickle.dump({'big':big,'P':out},open(S+'/comm.pkl','wb'))
_,C=co_graph(2024)
A=C.values.copy(); np.fill_diagonal(A,np.nan)
print('\nco-disruption correlation between airports, 2024: median',round(float(np.nanmedian(A)),3),'p90',round(float(np.nanpercentile(A,90)),3),'max',round(float(np.nanmax(A)),3))
for a,b in [('EWR','LGA'),('EWR','JFK'),('ORD','MDW'),('DFW','DAL'),('SFO','OAK'),('ATL','SEA'),('JFK','LAX')]:
    if a in C and b in C: print(' ',a,b,round(float(C.loc[a,b]),3))
