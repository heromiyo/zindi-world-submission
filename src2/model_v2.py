"""Model v2: organiser coverage-gap formula evaluated in expectation, references replaced by
proxies built only from the challenge package (Overture roads/places/buildings, ACS, tract tables)."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
ROOT=Path(__file__).resolve().parents[1]
REG=['eastern-ok','maricopa-az','northern-ca','south-central-tx']
NAMED=['motorway','trunk','primary','secondary']
DEFAULT=dict(w_I=1.0,w_US=1.0,w_ST=1.0,w_FM=1.0,w_STSUB=0.5,w_CR=0.0,w_mw_none=1.0,w_named_none=0.0,
             min_ref_m=300.0,sigma_T=0.35,b_gap=0.005,e_scale=1.0,fac_scale=1.0,recall=0.7,school_only=False)
def lognormal_gap(o,ref,sigma):
    """E[max(0,1-o/R)] with R ~ lognormal(median=ref, sigma)."""
    o=np.maximum(o,0);ref=np.maximum(ref,1e-9);out=np.zeros_like(ref)
    pos=ref>0
    z=(np.log(ref[pos])-np.log(np.maximum(o[pos],1e-9)))/sigma
    out[pos]=norm.cdf(z)-(o[pos]/ref[pos])*np.exp(.5*sigma**2)*norm.cdf(z-sigma)
    out[pos&(o<=0)]=1.0
    return np.clip(out,0,1)
def road_table(fname='road-routes2.parquet'):
    out=[]
    for r in REG:
        a=pd.read_parquet(ROOT/f'outputs/{r}/{fname}')
        a['named']=a.cls.isin(NAMED)
        w=a.pivot_table(index='GEOID',columns='kind',values='len',aggfunc='sum',fill_value=0).add_prefix('k_')
        w['o_named']=a[a.named].groupby('GEOID').len.sum()
        w['mw_none']=a[(a.cls=='motorway')&(a.kind=='none')].groupby('GEOID').len.sum()
        w['named_none']=a[a.named&(a.kind=='none')].groupby('GEOID').len.sum()
        w['tert_none']=a[(a.cls=='tertiary')&(a.kind=='none')].groupby('GEOID').len.sum()
        out.append(w.fillna(0))
    return pd.concat(out)
def build(prm=None,roads=None,base=None):
    prm={**DEFAULT,**(prm or {})}
    d=(base if base is not None else pd.read_parquet(ROOT/'outputs/structural.parquet')).copy()
    roads=roads if roads is not None else road_table()
    rt=roads.reindex(d.GEOID).fillna(0)
    g=lambda c:rt[c].to_numpy() if c in rt else np.zeros(len(d))
    ref=(prm['w_I']*g('k_I')+prm['w_US']*g('k_US')+prm['w_ST']*g('k_ST')+prm['w_FM']*g('k_FM')+prm['w_STSUB']*g('k_STSUB')
         +prm['w_CR']*g('k_CR')+prm['w_mw_none']*g('mw_none')+prm['w_named_none']*g('named_none'))
    o=g('o_named')
    dT=(ref>=prm['min_ref_m']).astype(float)
    T=np.where(dT>0,lognormal_gap(o,ref,prm['sigma_T']),0.0)
    # POI: facility half from structural.py expectations; establishments half scaled
    F=np.clip(d.F.to_numpy()*prm['fac_scale'],0,1);Fd=d.F_def.to_numpy();E=np.clip(d.E.to_numpy()*prm['e_scale'],0,1)
    P=Fd*(.5*F+.5*E)+(1-Fd)*E
    B=np.full(len(d),prm['b_gap']);dB=(d.building_count.to_numpy()>0).astype(float)
    y=(dT*T+dB*B+P)/(dT+dB+1)
    scored=(d.region!='eastern-wa').to_numpy()
    y=np.where(scored,y,0.0)
    d=d.assign(ref_m=ref,o_named=o,T_def=dT,Tgap=T,P=P,pred=y)
    return d
def diagnostics(d):
    s=d[d.region!='eastern-wa']
    rows=[]
    for r,x in s.groupby('region'):
        rows.append({'region':r,'O/R ratio':x.o_named.sum()/max(x.ref_m.sum(),1),'T_undef_frac':1-x.T_def.mean(),'mean_T|def':x.Tgap[x.T_def>0].mean(),'mean_pred':x.pred.mean()})
    return pd.DataFrame(rows)
if __name__=='__main__':
    import sys;fname=sys.argv[1] if len(sys.argv)>1 else 'road-routes2.parquet'
    d=build(roads=road_table(fname));print(diagnostics(d).round(3).to_string(index=False))
