"""Per-tract facility 'sibling' counts: places whose primary OR alternate category indicates fire/EMS/school,
plus primary-only counts. Permitted Overture places only."""
import sys
from pathlib import Path
import geopandas as gpd, pandas as pd, numpy as np, pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from spatial import assign_points
SCH={'elementary_school','middle_school','high_school','school','private_school','public_school'}
FIRE={'fire_department','fire_protection_service','fire_station'}
EMS={'ambulance_and_ems_services','emergency_service','emergency_medical_service'}
def kinds(cat):
    if not isinstance(cat,dict):return set(),set()
    pr=cat.get('primary');alt=cat.get('alternate');alt=set(alt) if alt is not None else set()
    allc={pr}|alt
    a={t for t,S in [('fire',FIRE),('ems',EMS),('school',SCH)] if allc&S}
    return a,allc
def run(r):
    t=gpd.read_parquet(ROOT/f'data/strata/{r}/{r}-census-tracts.parquet')[['GEOID','geometry']].to_crs('OGC:CRS84').sort_values('GEOID').reset_index(drop=True)
    acc=[]
    for b in pq.ParquetFile(ROOT/f'data/reference/{r}/{r}-overture-pois.parquet').iter_batches(batch_size=50000,columns=['categories','geometry','operating_status']):
        d=b.to_pandas();k=d.categories.map(lambda c:kinds(c)[0])
        m=k.map(len)>0;d=d[m];k=k[m]
        if not len(d):continue
        g=gpd.GeoDataFrame({'k':k.values,'closed':d.operating_status.eq('permanently_closed').values},geometry=gpd.GeoSeries.from_wkb(d.geometry.values,crs='OGC:CRS84'),crs='OGC:CRS84')
        ids,_=assign_points(g,t);g['GEOID']=ids.to_numpy();g=g.dropna(subset=['GEOID'])
        for ty in ['fire','ems','school']:
            s=g[g.k.map(lambda x:ty in x)]
            acc.append(s.groupby('GEOID').size().rename(f'{ty}_any').to_frame())
            acc.append(s[~s.closed].groupby('GEOID').size().rename(f'{ty}_any_open').to_frame())
    a=pd.concat(acc).groupby(level=0).sum().reindex(t.GEOID,fill_value=0).fillna(0).rename_axis('GEOID').reset_index()
    a.to_parquet(ROOT/f'outputs/{r}/poi-alt.parquet',index=False);print(r,a.drop(columns='GEOID').gt(0).mean().round(3).to_dict(),flush=True)
if __name__=='__main__':run(sys.argv[1])
