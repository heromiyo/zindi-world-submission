"""Tract frame for the Bias Discovery: strata, routed road length outside compared classes, primary and any-category EMS/fire counts."""
import pandas as pd
REG=['eastern-ok','maricopa-az','northern-ca','south-central-tx']
NAMED={'motorway','trunk','primary','secondary'}
rows=[]
for r in REG:
    s=pd.read_parquet(f'data/strata/{r}/{r}-strata-tract-table.parquet',columns=['GEOID','tribal_any','ur_class','pop_total','svi_overall','aiannh_name','ALAND'])
    a=pd.read_parquet(f'outputs/{r}/road-routes2.parquet');a['named']=a.cls.isin(NAMED)
    cr=a[(a.kind.isin(['CR','FM','STSUB']))&(~a.named)].groupby('GEOID').len.sum().rename('routed_outside_m')
    rt=a[a.kind!='none'].groupby('GEOID').len.sum().rename('routed_m')
    p=pd.read_parquet(f'outputs/{r}/poi-features.parquet')[['GEOID','fire_count','ems_count']]
    al=pd.read_parquet(f'outputs/{r}/poi-alt.parquet')
    d=s.merge(cr,on='GEOID',how='left').merge(rt,on='GEOID',how='left').merge(p,on='GEOID').merge(al,on='GEOID').fillna({'routed_outside_m':0,'routed_m':0})
    d['region']=r;rows.append(d)
d=pd.concat(rows);d['tribal']=d.tribal_any.astype(bool)
d.to_parquet('outputs/discovery-frame.parquet',index=False)
t=d[d.region=='eastern-ok'].groupby('tribal').routed_outside_m.sum().div(1000).round(0)
print('Eastern OK routed km outside compared classes, by tribal:',t.to_dict())
