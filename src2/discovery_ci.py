"""County-cluster bootstrap for the hidden-EMS discovery (tracts in one county are not independent)."""
import numpy as np, pandas as pd
rng=np.random.default_rng(20261031)
d=pd.read_parquet('outputs/discovery-frame.parquet')
h=pd.read_csv('reports/discovery/ems-alternate-only-records.csv',dtype={'GEOID':str})
d['hidden']=(d.ems_count==0)&d.GEOID.isin(h.GEOID);d['prim']=d.ems_count>0;d['cty']=d.GEOID.str[:5]
d=d[d.ur_class.isin(['Rural','Urban'])]
def stat(x):
    r=x[x.ur_class=='Rural'];u=x[x.ur_class=='Urban']
    vr=r.prim.sum()/(r.prim.sum()+r.hidden.sum());vu=u.prim.sum()/(u.prim.sum()+u.hidden.sum())
    return r.hidden.mean()-u.hidden.mean(),vr,vu
rows=[]
for reg,x in [('all four',d)]+list(d.groupby('region')):
    est=stat(x);c=x.cty.unique();g=dict(tuple(x.groupby('cty')));bs=[]
    for _ in range(1000):
        s=pd.concat([g[k] for k in rng.choice(c,len(c))]);bs.append(stat(s))
    bs=np.array(bs);lo,hi=np.percentile(bs,[2.5,97.5],axis=0)
    rows.append({'region':reg,'counties':len(c),'rural_minus_urban_hidden_pp':round(100*est[0],1),'ci95_pp':f'{100*lo[0]:.1f} to {100*hi[0]:.1f}',
                 'visible_share_rural':round(est[1],3),'ci_rural':f'{lo[1]:.3f}-{hi[1]:.3f}','visible_share_urban':round(est[2],3),'ci_urban':f'{lo[2]:.3f}-{hi[2]:.3f}'})
t=pd.DataFrame(rows);print(t.to_string(index=False));t.to_csv('reports/discovery/ems-hidden-ci.csv',index=False)
