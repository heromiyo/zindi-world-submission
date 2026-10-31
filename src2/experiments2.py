import numpy as np, pandas as pd, json, geopandas as gpd
from scipy.optimize import minimize_scalar, minimize
import model_v2 as m, evaluate as e
from experiments import fit, score, BLEND, roads, BASE
log=json.load(open('../outputs/experiments-log.json'))
P4=np.load('../outputs/R_best.npy')
def affine(p):
    """global a+b*p chosen by central estimate (constant direction is an own probe -> exact part)."""
    f=lambda x:e.interval(np.where(e.SCORED,np.clip(x[0]+x[1]*p,0,1),0))['central']
    r=minimize(f,[0.0,1.0],method='Nelder-Mead');return np.where(e.SCORED,np.clip(r.x[0]+r.x[1]*p,0,1),0),r.x
q,ab=affine(P4);score(f'6 affine calib of v2 a={ab[0]:.4f} b={ab[1]:.3f}',q,log)
# 7 facility numerators incl. alternate-category matches (fire_protection_service etc.) -> richer presence signal
# 8 tertiary-share road-mix: unrouted tertiary vs compared classes inflates transport gap where reference may count them
def post_tert(d,p):
    tert=d.GEOID.map(roads.tert_none).fillna(0).to_numpy();o=d.o_named.to_numpy()
    share=tert/(tert+o+500);return np.where(e.SCORED,p*(1+0.0)+0.05*share,0)
p8,_=fit(dict(w_STSUB=1.0,w_CR=0.45,min_ref_m=100,w_named_none=0.0),post=post_tert);score('8 + tertiary-share term',p8,log)
# 9 county-level spatial smoothing (shrink each tract 30% toward county mean of prediction)
def smooth(p,lam=0.3):
    s=pd.Series(p);cty=e.GEOID.str[:5];cm=s.groupby(cty.values).transform('mean').to_numpy();return np.where(e.SCORED,(1-lam)*p+lam*cm,0)
score('9 county smoothing 0.3 of v2',smooth(P4),log)
cands={'v2':P4,'v2_aff':q,'v2_tert':p8,'v2_smooth':smooth(P4)}
best=min(cands,key=lambda k:e.interval(cands[k])['central'])
for a in [0.4,0.5,0.6]:
    score(f'10 mix {a}*{best} + {1-a:.1f}*blend',a*cands[best]+(1-a)*BLEND,log)
json.dump(log,open('../outputs/experiments-log.json','w'),indent=1)
for k,v in cands.items():np.save(f'../outputs/cand_{k}.npy',v)
