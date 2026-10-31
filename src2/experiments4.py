"""#7 sibling-category facility signal + robustness checks."""
import numpy as np, pandas as pd, json
import evaluate as e
from experiments import fit, score, BLEND, BASE
from experiments2 import affine, smooth, post_tert
log=json.load(open('../outputs/experiments-log.json'))
REG=['eastern-ok','maricopa-az','northern-ca','south-central-tx','eastern-wa']
alt=pd.concat([pd.read_parquet(f'../outputs/{r}/poi-alt.parquet') for r in REG]).set_index('GEOID')
def base_with_sib(boost):
    d=BASE.copy();a=alt.reindex(d.GEOID).fillna(0)
    num=np.zeros(len(d));den=np.zeros(len(d))
    for t in ['fire','ems','school']:
        o=d[f'{t}_count'].to_numpy();sib=a[f'{t}_any'].to_numpy()-o
        pdef=d[f'pdef_{t}'].to_numpy()
        pdef=np.where((o==0)&(sib>0),np.maximum(pdef,boost),pdef)
        gap=np.where(o>0,0.5/(o+1),1.0)
        num+=pdef*gap;den+=pdef
    d['F']=num/np.maximum(den,1e-9)
    d['F_def']=1-np.prod([1-np.where((d[f'{t}_count'].to_numpy()==0)&(a[f'{t}_any'].to_numpy()>0),np.maximum(d[f'pdef_{t}'],boost),d[f'pdef_{t}']) for t in ['fire','ems','school']],axis=0)
    return d
def pipeline(base,lam=0.5):
    p,prm=fit(dict(w_STSUB=1.0,w_CR=0.45,min_ref_m=100),base=base,post=post_tert)
    q,ab=affine(smooth(p,lam));return q,prm,ab
if __name__=='__main__':
    res={}
    for boost in [0.5,0.8]:
        q,prm,ab=pipeline(base_with_sib(boost));res[boost]=q
        score(f'7 sibling-category facility signal boost={boost} (+tert+smooth+affine)',q,log)
    b=min(res,key=lambda k:e.interval(res[k])['central']);np.save('../outputs/cand_sib.npy',res[b])
    json.dump(log,open('../outputs/experiments-log.json','w'),indent=1)
