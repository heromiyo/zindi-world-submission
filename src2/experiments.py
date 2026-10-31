"""Improvement ladder: each variant refit on own-probe moments, scored by rigorous interval (own+yardstick span)."""
import numpy as np, pandas as pd, json
from scipy.optimize import minimize
import model_v2 as m, evaluate as e
roads=m.road_table();BASE=pd.read_parquet('../outputs/structural.parquet')
own=[(v,b) for v,b,r in e.K_OWN.values()]
BLEND=e.vec('submissions/blend/prediction.csv')
def fit(fix,free=('fac_scale','e_scale','b_gap','sigma_T'),x0=None,base=BASE,post=None):
    x0=np.log(x0 or [0.3,0.3,0.01,0.5][:len(free)])
    def mk(x):
        d=m.build({**fix,**dict(zip(free,np.exp(x)))},roads,base);p=d.pred.to_numpy()
        return post(d,p) if post else p
    def loss(x):
        p=mk(x)[e.SCORED];return float(sum((np.mean(v*p)/b-1)**2 for v,b in own))
    r=minimize(loss,x0,method='Nelder-Mead',options={'maxiter':250,'xatol':1e-3,'fatol':1e-7})
    return mk(r.x),dict(zip(free,np.exp(r.x).round(4)))
def score(name,p,log):
    iv=e.interval(p);log.append({'step':name,**{k:round(v,5) for k,v in iv.items()},'mean':round(float(p[e.SCORED].mean()),4)})
    print(log[-1],flush=True)
if __name__=='__main__':
    log=[];R={}
    score('0 own-probe blend (submitted-ready)',BLEND,log)
    p,_=fit(dict(w_STSUB=1.0,w_CR=0.0));R[1]=p;score('1 v2 transport: routes I/US/ST/FM, no county',p,log)
    p,_=fit(dict(w_STSUB=1.0,w_CR=0.45));R[2]=p;score('2 + county routes 0.45 (ratio 0.71-1.59 match)',p,log)
    p,_=fit(dict(w_STSUB=1.0,w_CR=0.45,min_ref_m=1000));R[3]=p;score('3 + min ref 1km for defined',p,log)
    p,_=fit(dict(w_STSUB=1.0,w_CR=0.45,min_ref_m=100));R[4]=p;score('4 + min ref 100m for defined',p,log)
    best=min([2,3,4],key=lambda k:e.interval(R[k])['central'])
    for a in [0.3,0.5,0.7]:
        score(f'5 mix {a}*v2[{best}] + {1-a}*blend',a*R[best]+(1-a)*BLEND,log)
    json.dump(log,open('../outputs/experiments-log.json','w'),indent=1)
    np.save('../outputs/R_best.npy',R[best])
