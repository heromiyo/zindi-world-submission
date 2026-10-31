"""Fit a handful of global parameters of model v2 to own-probe moments; validate on held-out yardsticks."""
import numpy as np, pandas as pd, json
from scipy.optimize import minimize
import model_v2 as m, evaluate as e
roads=m.road_table();base=pd.read_parquet('../outputs/structural.parquet')
FIX=dict(w_STSUB=1.0,w_CR=0.45)
NAMES=['fac_scale','e_scale','b_gap','sigma_T']
def unpack(x):return dict(fac_scale=np.exp(x[0]),e_scale=np.exp(x[1]),b_gap=np.exp(x[2]),sigma_T=np.exp(x[3]))
own=[(v,b) for v,b,r in e.K_OWN.values()]
def moments(p):
    p=p[e.SCORED];return np.array([np.mean(v*p)/b-1 for v,b in own])
def loss(x):
    d=m.build({**FIX,**unpack(x)},roads,base);return float(np.sum(moments(d.pred.to_numpy())**2))
x0=np.log([0.5,0.5,0.01,0.35])
res=minimize(loss,x0,method='Nelder-Mead',options={'maxiter':300,'xatol':1e-3,'fatol':1e-7})
prm={**FIX,**unpack(res.x)};print('fit',{k:round(v,4) for k,v in prm.items()},'loss',res.fun)
d=m.build(prm,roads,base);print(m.diagnostics(d).round(3).to_string(index=False))
s=e.report(d.pred,'v2-fit');print(s)
json.dump(prm,open('../outputs/v2-params.json','w'),indent=1)
d[['GEOID','pred']].to_parquet('../outputs/v2-pred.parquet',index=False)
