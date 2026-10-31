"""Per-tract Overture road length by class (motorway/trunk/primary/secondary/tertiary), segment midpoint assignment."""
import sys
from pathlib import Path
import geopandas as gpd, pandas as pd, pyarrow.parquet as pq, shapely
ROOT=Path(__file__).resolve().parents[1]
KEEP=['motorway','trunk','primary','secondary','tertiary']
def run(r):
    t=gpd.read_parquet(ROOT/f'data/strata/{r}/{r}-census-tracts.parquet',columns=['GEOID','geometry']).to_crs(5070)
    t['GEOID']=t.GEOID.astype(str).str.zfill(11)
    out=[]
    for b in pq.ParquetFile(ROOT/f'data/projected/{r}-roads.parquet').iter_batches(batch_size=200000):
        d=b.to_pandas();d=d[d['class'].isin(KEEP)]
        if not len(d):continue
        g=gpd.GeoDataFrame({'cls':d['class'].values},geometry=gpd.GeoSeries.from_wkb(d.geometry.values,crs=4326)).to_crs(5070)
        g['len']=g.length;g['geometry']=shapely.line_interpolate_point(g.geometry.values,0.5,normalized=True)
        j=gpd.sjoin(g,t,how='inner',predicate='within')
        out.append(j.groupby(['GEOID','cls'])['len'].sum())
    a=pd.concat(out).groupby(level=[0,1]).sum().unstack(fill_value=0).reindex(t.GEOID,fill_value=0)
    a.columns=[f'len_{c}' for c in a.columns];a=a.reset_index()
    a.to_parquet(ROOT/f'outputs/{r}/road-classes.parquet',index=False);print(r,a.shape,flush=True)
if __name__=='__main__':run(sys.argv[1])
