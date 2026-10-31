"""Bias discovery evidence: EMS services that Overture lists only under an alternate category."""
import pandas as pd, geopandas as gpd, sys
sys.path.insert(0,'src');from spatial import assign_points
EMS={'ambulance_and_ems_services','emergency_service','emergency_medical_service'}
def alt_ems(c):
    if not isinstance(c,dict):return False
    a=c.get('alternate');a=set(a) if a is not None else set()
    return c.get('primary') not in EMS and bool(a&EMS)
out=[]
for r in ['eastern-ok','south-central-tx','northern-ca','maricopa-az']:
    p=pd.read_parquet(f'data/reference/{r}/{r}-overture-pois.parquet',columns=['id','names','categories','geometry','operating_status','sources'])
    p=p[p.categories.map(alt_ems)].reset_index(drop=True)
    t=gpd.read_parquet(f'data/strata/{r}/{r}-census-tracts.parquet')[['GEOID','geometry']].to_crs('OGC:CRS84').sort_values('GEOID').reset_index(drop=True)
    g=gpd.GeoDataFrame(p.drop(columns='geometry'),geometry=gpd.GeoSeries.from_wkb(p.geometry.values,crs='OGC:CRS84'),crs='OGC:CRS84')
    ids,_=assign_points(g,t);g['GEOID']=ids.to_numpy()
    g['primary']=g.categories.map(lambda c:c.get('primary'));g['name']=g.names.map(lambda n:n.get('primary') if isinstance(n,dict) else '')
    g['src']=g.sources.map(lambda s:s[0].get('dataset') if s is not None and len(s) else '')
    out.append(pd.DataFrame(g[['id','GEOID','name','primary','operating_status','src']]).assign(region=r,lon=g.geometry.x,lat=g.geometry.y))
a=pd.concat(out);a.to_csv('reports/discovery/ems-alternate-only-records.csv',index=False)
d=pd.read_parquet('outputs/discovery-frame.parquet')
x=a.merge(d[['GEOID','ur_class','tribal','aiannh_name','ems_count','pop_total','svi_overall']],on='GEOID')
print('records',len(a),'assigned',x.shape[0])
print(x.primary.value_counts().head(5).to_dict())
hid=x[x.ems_count==0]
print('tracts where EMS appears only as alternate:',hid.GEOID.nunique())
print(hid.drop_duplicates('GEOID').groupby(['region','ur_class']).size().unstack().to_string())
# tract-level table by strata
d['ems_hidden']=(d.ems_count==0)&d.GEOID.isin(hid.GEOID)
t=d.groupby(['region','ur_class']).agg(tracts=('GEOID','size'),ems_primary=('ems_count',lambda s:(s>0).mean()),ems_hidden=('ems_hidden','mean')).round(3)
t['visible_share_of_known_EMS_tracts']=(t.ems_primary/(t.ems_primary+t.ems_hidden)).round(3)
print(t.to_string());t.to_csv('reports/discovery/ems-hidden-by-stratum.csv')
tt=d[d.region=='eastern-ok'].groupby('tribal').agg(tracts=('GEOID','size'),ems_primary=('ems_count',lambda s:(s>0).mean()),ems_hidden=('ems_hidden','mean')).round(3);print(tt.to_string());tt.to_csv('reports/discovery/ems-hidden-eastern-ok-tribal.csv')
ex=hid[hid.ur_class=='Rural'].sort_values('pop_total',ascending=False).drop_duplicates('GEOID')
print(ex[['region','GEOID','name','primary','aiannh_name','pop_total','svi_overall']].head(12).to_string(index=False))
ex.to_csv('reports/discovery/ems-hidden-rural-tracts.csv',index=False)
