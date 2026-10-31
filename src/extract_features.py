"""Batch spatial aggregation of permitted Overture POIs. No target/reference denominators."""
from pathlib import Path
import json, re
import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from download import REGIONS
from spatial import assign_points
ROOT=Path(__file__).resolve().parents[1]
SCHOOLS={'elementary_school','middle_school','high_school','school','private_school','public_school'}
TYPES={'fire_department':'fire','ambulance_and_ems_services':'ems','hospital':'hospital',**{s:'school' for s in SCHOOLS}}
def run(region):
 out=ROOT/'outputs'/region;out.mkdir(exist_ok=True)
 tracts=gpd.read_parquet(ROOT/f'data/strata/{region}/{region}-census-tracts.parquet')
 tracts['GEOID']=tracts.GEOID.astype(str).str.zfill(11)
 tracts=tracts[['GEOID','geometry']].to_crs('OGC:CRS84').sort_values('GEOID').reset_index(drop=True)
 aggregates=[];facilities=[];diagnostics={'region':region,'input_pois':0,'matched_pois':0,'outside_tracts':0,'multiple_matches':0}
 f=pq.ParquetFile(ROOT/f'data/reference/{region}/{region}-overture-pois.parquet')
 cols=['id','categories','confidence','names','sources','operating_status','phones','websites','addresses','geometry']
 for batch in f.iter_batches(batch_size=40000,columns=cols):
  d=batch.to_pandas();diagnostics['input_pois']+=len(d)
  g=gpd.GeoDataFrame(d,geometry=gpd.GeoSeries.from_wkb(d.geometry,crs='OGC:CRS84'),crs='OGC:CRS84')
  ids,dd=assign_points(g,tracts)
  diagnostics['multiple_matches']+=dd['extra_boundary_matches']
  diagnostics['outside_tracts']+=dd['unmatched']
  diagnostics['matched_pois']+=dd['matched']
  j=g.copy();j['GEOID']=ids.to_numpy();j=j.dropna(subset=['GEOID'])
  j['category']=j.categories.map(lambda c:c.get('primary') if isinstance(c,dict) else None)
  j['facility_type']=j.category.map(TYPES)
  j['has_phone']=j.phones.map(lambda a: a is not None and any(str(v).strip() for v in a))
  j['has_website']=j.websites.map(lambda a:a is not None and any(str(v).strip() for v in a))
  j['has_address']=j.addresses.map(lambda a:a is not None and any(v.get('freeform') for v in a))
  j['closed']=j.operating_status.eq('permanently_closed')
  j['low_confidence']=j.confidence.lt(.5)
  j['count']=1
  group=j.groupby('GEOID')[['count','has_phone','has_website','has_address','closed','low_confidence']].sum().add_prefix('poi_')
  group['poi_confidence_sum']=j.groupby('GEOID').confidence.sum()
  for t in ['fire','ems','school','hospital']:
   z=j[j.facility_type.eq(t)];gg=z.groupby('GEOID')[['count','has_phone','has_website','has_address','closed','low_confidence']].sum().add_prefix(t+'_');group=group.join(gg)
  aggregates.append(group.fillna(0))
  z=j[j.facility_type.notna()].copy()
  z['name']=z.names.map(lambda c:c.get('primary') if isinstance(c,dict) else '')
  z['lon']=z.geometry.x;z['lat']=z.geometry.y
  z['phone']=z.phones.map(lambda a:' | '.join(a) if a is not None else '')
  z['website']=z.websites.map(lambda a:' | '.join(a) if a is not None else '')
  z['address']=z.addresses.map(lambda a:' | '.join(v.get('freeform') or '' for v in a) if a is not None else '')
  z['datasets']=z.sources.map(lambda a:' | '.join(sorted(set(v.get('dataset') or '' for v in a if v.get('dataset')!='Overture'))) if a is not None else '')
  z['source_update']=z.sources.map(lambda a:max((v.get('update_time') or '' for v in a if v.get('dataset')!='Overture'),default='') if a is not None else '')
  facilities.append(pd.DataFrame(z[['GEOID','id','facility_type','category','name','lon','lat','confidence','operating_status','has_phone','has_website','has_address','phone','website','address','datasets','source_update']]))
  print(region,diagnostics['input_pois'],flush=True)
 agg=pd.concat(aggregates).groupby(level=0).sum().reindex(tracts.GEOID,fill_value=0).rename_axis('GEOID').reset_index()
 agg.to_parquet(out/'poi-features.parquet',index=False)
 pd.concat(facilities).to_csv(out/'facility-audit.csv',index=False)
 (out/'spatial-diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
 if diagnostics['matched_pois']+diagnostics['outside_tracts']!=diagnostics['input_pois']:raise ValueError('POI conservation failed')
 print('DONE',region,diagnostics,flush=True)
if __name__=='__main__':
 import sys
 for r in sys.argv[1:] or REGIONS:run(r)
