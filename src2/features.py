"""Assemble per-tract features from provided data only (no reference layers)."""
from pathlib import Path
import pandas as pd, numpy as np
ROOT=Path(__file__).resolve().parents[1]
REG=['eastern-ok','maricopa-az','northern-ca','south-central-tx','eastern-wa']
STRATA=['GEOID','ALAND','pop_total','pct_urban','ur_class','tribal_any','svi_overall','ruca_primary']
def load():
    out=[]
    for r in REG:
        s=pd.read_parquet(ROOT/f'data/strata/{r}/{r}-strata-tract-table.parquet',columns=STRATA)
        for f in ['poi-features','roads-features','buildings-features']+(['road-classes'] if r!='eastern-wa' else []):
            s=s.merge(pd.read_parquet(ROOT/f'outputs/{r}/{f}.parquet'),on='GEOID',how='left')
        h=pd.read_csv(ROOT/f'data/reference/{r}/{r}-census-acs-housing.csv',dtype={'GEOID':str})[['GEOID','housing_units']]
        s=s.merge(h,on='GEOID',how='left');s['region']=r;out.append(s)
    d=pd.concat(out,ignore_index=True)
    sub=pd.read_csv(ROOT/'data/SampleSubmission.csv',dtype={'GEOID':str},usecols=['GEOID'])
    d=sub.merge(d,on='GEOID',how='left',validate='one_to_one')
    return d.fillna({c:0 for c in d.columns if c.startswith('len_')})
if __name__=='__main__':
    d=load();d.to_parquet(ROOT/'outputs/features2.parquet',index=False)
    d['mtp']=d.len_motorway+d.len_trunk+d.len_primary
    d['named']=d.mtp+d.len_secondary
    for r,g in d.groupby('region'):
        print(r,len(g),'mtp0',(g.mtp==0).mean().round(3),'named0',(g.named==0).mean().round(3),'sec0',(g.len_secondary==0).mean().round(3),
              'bld/hu med',(g.building_count/g.housing_units.clip(1)).median().round(2),'hu0',(g.housing_units==0).mean().round(3),'pop0',(g.pop_total==0).mean().round(3))
