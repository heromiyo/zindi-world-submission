"""Project only permitted Overture columns into a local cache; no hidden references.
Buildings: bbox-centre assignment, checked against sampled representative points.
Roads: polygon intersections in CRS84; ellipsoidal WGS84 lengths. Boundary overlap
is allocated in lexical GEOID order so a line is never counted twice.
"""
from pathlib import Path
import hashlib,json
import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from pyarrow.fs import S3FileSystem
import shapely
from download import REGIONS
from spatial import assign_points,geodesic_length,geodesic_lengths
ROOT=Path(__file__).resolve().parents[1]
PREFIX='us-west-2.opendata.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge/reference'
HIGHWAYS={'motorway','trunk','primary','secondary'}
def projected_cache(region,layer,cols,fs):
    dest=ROOT/f'data/projected/{region}-{layer}.parquet';dest.parent.mkdir(parents=True,exist_ok=True)
    path=f'{PREFIX}/{region}/{region}-overture-{layer}.parquet'
    remote=pq.ParquetFile(path,filesystem=fs)
    if not dest.exists():
        tmp=dest.with_suffix('.part');writer=None
        try:
            for b in remote.iter_batches(batch_size=40000,columns=cols):
                if writer is None:writer=pq.ParquetWriter(tmp,b.schema,compression='zstd')
                writer.write_batch(b)
            if writer:writer.close();writer=None
            tmp.rename(dest)
        finally:
            if writer:writer.close()
    info={'url':'https://s3.us-west-2.amazonaws.com/'+path,'columns':cols,
          'rows':remote.metadata.num_rows,'remote_footer_sha256':hashlib.sha256(repr(remote.metadata.to_dict()).encode()).hexdigest(),
          'projected_cache':str(dest.relative_to(ROOT)),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    return dest,remote,info

def check_building_approx(remote,tracts):
    rng=np.random.default_rng(20261023);rows=[];worst=0
    groups=sorted(rng.choice(remote.num_row_groups,size=min(3,remote.num_row_groups),replace=False).tolist())
    for rg in groups:
        d=remote.read_row_group(rg,columns=['bbox','geometry']).to_pandas()
        d=d.iloc[np.sort(rng.choice(len(d),size=min(256,len(d)),replace=False))].reset_index(drop=True)
        bb=pd.DataFrame(d.bbox.tolist())
        centres=gpd.GeoDataFrame(geometry=gpd.points_from_xy((bb.xmin+bb.xmax)/2,(bb.ymin+bb.ymax)/2),crs=tracts.crs)
        polys=gpd.GeoSeries.from_wkb(d.geometry,crs=tracts.crs)
        reps=gpd.GeoDataFrame(geometry=polys.representative_point(),crs=tracts.crs)
        a,_=assign_points(centres,tracts);b,_=assign_points(reps,tracts)
        outside=~shapely.covers(polys.to_numpy(),centres.geometry.to_numpy())
        rows.append({'row_group':rg,'sampled':len(d),'assignment_disagreements':int((a.fillna('NONE')!=b.fillna('NONE')).sum()),'bbox_centre_outside_footprint':int(outside.sum())})
    return {'sampling':'three fixed-seed random row groups, up to256 random records per group; diagnostic only, not exhaustive accuracy certification','groups':rows}

def run(region):
    out=ROOT/'outputs'/region;out.mkdir(exist_ok=True)
    t=gpd.read_parquet(ROOT/f'data/strata/{region}/{region}-census-tracts.parquet')[['GEOID','geometry']].to_crs('OGC:CRS84')
    t.GEOID=t.GEOID.astype(str).str.zfill(11);t=t.sort_values('GEOID').reset_index(drop=True)
    shapely.prepare(t.geometry.to_numpy())
    fs=S3FileSystem(anonymous=True,region='us-west-2',request_timeout=120,connect_timeout=30)
    diag={'region':region,'version':2,'length_units':'ellipsoidal WGS84 metres','building_assignment':'bbox-centre, smallest GEOID tie break','sources':[]}
    for layer,cols in [('buildings',['bbox']),('roads',['geometry','class'])]:
        cache,remote,info=projected_cache(region,layer,cols,fs);diag['sources'].append(info)
        accum=[];seen=0;miss=0;ties=0;input_length=0.;assigned_length=0.;overlap_removed=0.
        for b in pq.ParquetFile(cache).iter_batches(batch_size=40000):
            d=b.to_pandas();seen+=len(d)
            if layer=='buildings':
                bb=pd.DataFrame(d.bbox.tolist());g=gpd.GeoDataFrame(geometry=gpd.points_from_xy((bb.xmin+bb.xmax)/2,(bb.ymin+bb.ymax)/2),crs=t.crs)
                ids,dd=assign_points(g,t);miss+=dd['unmatched'];ties+=dd['extra_boundary_matches']
                a=ids.dropna().value_counts().rename('building_count').to_frame()
            else:
                g=gpd.GeoDataFrame({'highway':d['class'].isin(HIGHWAYS).to_numpy(),'_row':np.arange(len(d))},geometry=gpd.GeoSeries.from_wkb(d.geometry,crs=t.crs),crs=t.crs)
                j=gpd.sjoin(g,t,how='inner',predicate='intersects').sort_values(['_row','GEOID'])
                polys=t.geometry.iloc[j.index_right.astype(int)].to_numpy();line=j.geometry.to_numpy()
                covered_mask=shapely.covers(polys,line);clip=line.copy()
                clip[~covered_mask]=shapely.intersection(line[~covered_mask],polys[~covered_mask])
                lens=geodesic_lengths(clip);j['metres']=lens
                multiple=j._row.value_counts();multiple=set(multiple.index[multiple>1])
                indexed=j.reset_index(drop=True);groups=indexed[indexed._row.isin(multiple)].groupby('_row').groups
                for _,pos in groups.items():
                    positions=np.asarray(pos)
                    if len(positions)<2:continue
                    # Subtract only already assigned line fragments; shared points have zero length.
                    covered=None
                    for k in positions:
                        geom=clip[k];unique=geom if covered is None else shapely.difference(geom,covered)
                        new=geodesic_length(unique);overlap_removed+=max(0.,lens[k]-new);lens[k]=new
                        covered=geom if covered is None else shapely.union(covered,geom)
                j['metres']=lens;j['highway_metres']=lens*j.highway.to_numpy()
                original=float(geodesic_lengths(g.geometry.to_numpy()).sum());allocated=float(lens.sum())
                if allocated>original+max(.1,original*1e-6):raise ValueError('Road length conservation failed')
                input_length+=original;assigned_length+=allocated
                miss+=len(g)-j._row.nunique()
                a=j.groupby('GEOID')[['metres','highway_metres']].sum().rename(columns={'metres':'road_metres'})
            accum.append(a);print(region,layer,seen,'/',info['rows'],flush=True)
        agg=pd.concat(accum).groupby(level=0).sum().reindex(t.GEOID,fill_value=0).rename_axis('GEOID').reset_index()
        dest=out/f'{layer}-features.parquet';agg.to_parquet(dest,index=False)
        diag[layer]={'rows':seen,'unmatched':int(miss),'boundary_extra_matches':int(ties),'aggregate_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
        if layer=='buildings':
            if int(agg.building_count.sum())+miss!=seen:raise ValueError('Building conservation failed')
            diag['building_approximation_check']=check_building_approx(remote,t)
        else:diag['roads'].update(input_metres=input_length,assigned_metres=assigned_length,boundary_overlap_removed_metres=overlap_removed)
    (out/'network-diagnostics.json').write_text(json.dumps(diag,indent=2))
    print('DONE NETWORK',region,flush=True)
if __name__=='__main__':
    import sys
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run,sys.argv[1:] or REGIONS))
