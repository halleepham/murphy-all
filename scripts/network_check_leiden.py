# Quick check behind 0017, kept as run. Usage: PYTHONPATH=. python scripts/network_check_leiden.py data/forecast/network
import sys,pickle,duckdb,numpy as np,pandas as pd,networkx as nx
S=sys.argv[1]; sys.path.append(S+'/leiden_lib')
import igraph as ig, leidenalg as la
from networkx.algorithms.community import louvain_communities, modularity
from sklearn.metrics import adjusted_rand_score as ari
c=duckdb.connect(); big=pickle.load(open(S+'/comm.pkl','rb'))['big']
print('networkx leiden?',hasattr(nx.community,'leiden_communities'))
def panel(y):
    d=c.sql(f"""select origin a,time_bucket(interval 3 hour,sched_dep_utc) t,avg(case when cancelled or dep_delay_min>=15 then 1.0 else 0.0 end) s,count(*) n from read_parquet('data/flights/{y}_*.parquet') group by 1,2""").df()
    d=d[d.a.isin(big)&(d.n>=3)]; d['h']=d.t.dt.hour; d['m']=d.t.dt.month; d['raw']=d.s; d['usual']=d.groupby(['a','h','m']).s.transform('mean'); d['x']=d.s-d.usual; return d
def co(d,top=8):
    C=d.pivot(index='t',columns='a',values='x').corr(min_periods=300).reindex(index=big,columns=big); A=C.values.copy(); np.fill_diagonal(A,np.nan); G=nx.Graph(); G.add_nodes_from(big)
    for i,a in enumerate(big):
        for j in np.argsort(-np.nan_to_num(A[i],nan=-9))[:top]:
            if A[i][j]>0: G.add_edge(a,big[j],weight=float(A[i][j]))
    return G
d3,d4=panel(2023),panel(2024); G3,G4=co(d3),co(d4)
def lab(cs): 
    m={n:i for i,x in enumerate(cs) for n in x}; return [m[n] for n in big]
def lei(G,seed):
    g=ig.Graph.from_networkx(G); names=g.vs['_nx_name']
    p=la.find_partition(g,la.ModularityVertexPartition,weights='weight',seed=seed,n_iterations=-1)
    return [{names[v] for v in cl} for cl in p]
for nm,f in (('louvain',lambda G,s:louvain_communities(G,weight='weight',seed=s)),('leiden',lei)):
    r=[f(G3,s) for s in range(30)]; r4=f(G4,0); L=[lab(x) for x in r]; mods=[modularity(G3,x,weight='weight') for x in r]
    disc=sum(not nx.is_connected(G3.subgraph(cm)) for x in r for cm in x)
    print(f"{nm}: groups {sorted(set(len(x) for x in r))}; modularity mean {np.mean(mods):.4f} best {max(mods):.4f}; seed agreement {np.mean([ari(L[0],l) for l in L[1:]]):.3f}; 2023 vs 2024 {ari(L[0],lab(r4)):.3f}; broken groups across 30 runs {disc}")
    globals()[nm]=L[int(np.argmax(mods))]
print('louvain vs leiden best runs agreement',round(ari(louvain,leiden),3))
# worked example
e=d4[d4.a.isin(['EWR','LGA','JFK','SEA'])].pivot(index='t',columns='a',values='x'); t=e.dropna().EWR.sort_values().index[-40]
print('example block',t); print(d4[(d4.t==t)&d4.a.isin(['EWR','LGA','JFK','SEA'])][['a','n','raw','usual','x']].round(3).to_string(index=False))
C=d4.pivot(index='t',columns='a',values='x'); print('blocks per airport pair EWR-LGA',len(C[['EWR','LGA']].dropna()))
print('edges in co graph 2023',G3.number_of_edges())
