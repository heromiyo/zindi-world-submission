"""Post-steps used by make_final.py (same code as in experiments2.py, without the experiment run on import)."""
import numpy as np, pandas as pd
from scipy.optimize import minimize
import evaluate as e
from experiments import roads
def affine(p):
    """global a+b*p chosen by central estimate (constant direction is an own probe -> exact part)."""
    f=lambda x:e.interval(np.where(e.SCORED,np.clip(x[0]+x[1]*p,0,1),0))['central']
    r=minimize(f,[0.0,1.0],method='Nelder-Mead');return np.where(e.SCORED,np.clip(r.x[0]+r.x[1]*p,0,1),0),r.x
def post_tert(d,p):
    tert=d.GEOID.map(roads.tert_none).fillna(0).to_numpy();o=d.o_named.to_numpy()
    share=tert/(tert+o+500);return np.where(e.SCORED,p*(1+0.0)+0.05*share,0)
def smooth(p,lam=0.3):
    s=pd.Series(p);cty=e.GEOID.str[:5];cm=s.groupby(cty.values).transform('mean').to_numpy();return np.where(e.SCORED,(1-lam)*p+lam*cm,0)
