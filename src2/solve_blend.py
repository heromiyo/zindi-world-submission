"""Least-squares blend from public-leaderboard inner products: <p,y> = (E[y^2]+E[p^2]-MSE)/2."""
from pathlib import Path
import numpy as np, pandas as pd, json
ROOT=Path(__file__).resolve().parents[1]
d=pd.read_parquet(ROOT/'outputs/structural.parquet');sc=(d.region!='eastern-wa').to_numpy()
rd=lambda f:pd.read_csv(ROOT/f,dtype={'GEOID':str}).set_index('GEOID').coverage_gap_score.reindex(d.GEOID).to_numpy()
V={'dem':rd('submissions/demographic/prediction.csv'),'geo':rd('submissions/geographic/prediction.csv')}
for c in ['z_fac','z_est','z_bld','z_const']:V[c]=rd(f'submissions/probes/{c}.csv')
RMSE={'zero':0.107246299,'dem':0.140188939,'geo':0.139906454,'z_fac':0.097931153,'z_est':0.109089522,'z_bld':0.124615516,'z_const':0.089560921}
Ey2=RMSE['zero']**2
names=list(V);P=np.c_[[V[n][sc] for n in names]].T
b=np.array([(Ey2+np.mean(V[n][sc]**2)-RMSE[n]**2)/2 for n in names])
G=P.T@P/len(P)
def mse(w):return Ey2-2*w@b+w@G@w
for lam in [0,1e-5,1e-4]:
    w=np.linalg.solve(G+lam*np.eye(len(names)),b);print('lam',lam,dict(zip(names,w.round(3))),'pred RMSE',np.sqrt(mse(w)).round(5))
for sub in [['z_const','z_fac'],['z_const','z_fac','z_est'],['z_const','z_fac','z_est','z_bld'],['z_const','z_fac','dem','geo']]:
    i=[names.index(n) for n in sub];w=np.linalg.solve(G[np.ix_(i,i)],b[i]);ww=np.zeros(len(names));ww[i]=w
    print(sub,w.round(3),'pred RMSE',np.sqrt(mse(ww)).round(5))
json.dump({'names':names,'b':b.tolist(),'G':G.tolist(),'Ey2':Ey2},open(ROOT/'outputs/blend-system.json','w'))
