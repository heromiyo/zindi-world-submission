"""Per-tract road lengths split by Overture class and by route network (permitted Overture roads only)."""
import sys,json
from pathlib import Path
import geopandas as gpd, pandas as pd, pyarrow.parquet as pq, shapely, numpy as np
from pyarrow.fs import S3FileSystem
ROOT=Path(__file__).resolve().parents[1]
P='us-west-2.opendata.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge/reference'
NAMED={'motorway','trunk','primary','secondary'}
STATE_SUB={'FM','RM','Loop','Spur','Business','Beltway','Park','Toll','Turnpike','NTTA','Trunk','Truck','Future','Alternate','Scenic'}
def net_kind(routes):
    if routes is None or len(routes)==0:return 'none'
    ks=set()
    for r in routes:
        n=(r.get('network') or '');p=n.split(':')
        if n.startswith('US:I'):ks.add('I')
        elif n.startswith('US:US'):ks.add('US')
        elif len(p)==2 and p[0]=='US' and len(p[1])==2:ks.add('ST')
        elif len(p)>=3 and p[0]=='US' and len(p[1])==2 and p[2] in ('FM','RM'):ks.add('FM')
        elif len(p)>=3 and p[0]=='US' and len(p[1])==2 and p[2] in STATE_SUB:ks.add('STSUB')
        elif len(p)>=3 and p[0]=='US' and len(p[1])==2:ks.add('CR')
        else:ks.add('OTHER')
    for k in ['I','US','ST','FM','STSUB','CR','OTHER']:
        if k in ks:return k
def run(r):
    t=gpd.read_parquet(ROOT/f'data/strata/{r}/{r}-census-tracts.parquet',columns=['GEOID','geometry']).to_crs(5070)
    fs=S3FileSystem(anonymous=True,region='us-west-2')
    f=pq.ParquetFile(f'{P}/{r}/{r}-overture-roads.parquet',filesystem=fs)
    out=[];nets={}
    for b in f.iter_batches(batch_size=100000,columns=['class','routes','geometry']):
        d=b.to_pandas()
        kind=d.routes.map(net_kind)
        for rs in d.routes.dropna():
            for x in rs:nets[x.get('network')]=nets.get(x.get('network'),0)+1
        keep=d['class'].isin(NAMED|{'tertiary'})|(kind!='none')
        d=d[keep];kind=kind[keep]
        g=gpd.GeoDataFrame({'cls':d['class'].values,'kind':kind.values},geometry=gpd.GeoSeries.from_wkb(d.geometry.values,crs=4326)).to_crs(5070)
        g=g.explode(index_parts=False)
        # clip segments to tracts so boundary roads split by length
        j=gpd.overlay(g,t,how='intersection',keep_geom_type=True)
        j['len']=j.length;j['named']=j.cls.isin(NAMED)
        out.append(j.groupby(['GEOID','cls','kind'])['len'].sum())
        print(r,'batch',flush=True)
    a=pd.concat(out).groupby(level=[0,1,2]).sum().reset_index()
    a.to_parquet(ROOT/f'outputs/{r}/road-routes2.parquet',index=False)
    json.dump(dict(sorted(nets.items(),key=lambda x:-x[1])[:60]),open(ROOT/f'outputs/{r}/route-networks.json','w'),indent=0)
if __name__=='__main__':run(sys.argv[1])
