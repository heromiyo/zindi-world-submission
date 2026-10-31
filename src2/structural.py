"""Structural expected-gap features from provided data only. Seeded, deterministic."""
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
ROOT=Path(__file__).resolve().parents[1]
RECALL=0.7  # assumed Overture recall for a facility type present in the reference
def build():
    d=pd.read_parquet(ROOT/'outputs/features2.parquet')
    scored=d.region!='eastern-wa'
    X=np.c_[np.log1p(d.pop_total),np.log1p(d.ALAND/1e6),d.pct_urban.fillna(0),np.log1p(d.poi_count),np.log1p(d.building_count),
            pd.get_dummies(d.region).to_numpy(float)]
    X=(X-X.mean(0))/(X.std(0)+1e-9)
    num=np.zeros(len(d));den=np.zeros(len(d))
    for t in ['fire','ems','school']:
        o=d[f'{t}_count'].to_numpy()
        w=LogisticRegression(C=1.0,max_iter=2000).fit(X,o>0).predict_proba(X)[:,1]
        a=np.clip(w/RECALL,0,0.999)                       # P(reference has type t)
        p_def0=np.clip(a*(1-RECALL)/(1-w+1e-9),0,1)        # P(ref>0 | overture=0)
        d[f'pdef_{t}']=np.where(o>0,1.0,p_def0)
        d[f'gap_{t}']=np.where(o>0,0.5/(o+1),1.0)          # expected per-type gap if defined
        num+=d[f'pdef_{t}']*d[f'gap_{t}'];den+=d[f'pdef_{t}']
    d['F']=num/np.maximum(den,1e-9);d['F_def']=1-np.prod([1-d[f'pdef_{t}'] for t in ['fire','ems','school']],axis=0)
    # establishments half: shortfall vs housing-scaled regional expectation of places
    hu=d.housing_units.clip(lower=1)
    rate=(d.poi_count/hu).groupby(d.region).transform('median')
    d['E']=np.clip(1-d.poi_count/(0.5*rate*hu),0,1)
    d['P']=d.F_def*(0.5*d.F+0.5*d.E)+(1-d.F_def)*d.E
    # building shortfall vs ACS housing units (sanity proxy only)
    d['B']=np.clip(1-d.building_count/(0.6*hu),0,1)*(d.housing_units>0)
    mtp=d.len_motorway+d.len_trunk+d.len_primary
    d['T_def']=np.where(mtp>0,0.8,0.3)
    n=1+(d.housing_units>0)+d.T_def
    d['z_fac']=d.F_def*0.5*d.F/n
    d['z_est']=(d.F_def*0.5+(1-d.F_def))*d.E/n
    d['z_bld']=d.B/n
    d['z_tr']=d.T_def/n
    d['z_const']=1.0
    d['S']=d.z_fac+d.z_est+d.z_bld
    for c in ['z_fac','z_est','z_bld','z_tr','z_const','S']:d.loc[~scored,c]=0.0
    return d
if __name__=='__main__':
    d=build();d.to_parquet(ROOT/'outputs/structural.parquet',index=False)
    s=d[d.region!='eastern-wa']
    print(s[['F','F_def','E','B','P','z_fac','z_est','z_bld','z_tr','S']].describe().T.round(3).to_string())
    print(s.groupby('region')[['z_fac','z_est','z_bld','S']].mean().round(3))
