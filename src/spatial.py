"""Deterministic point membership and geodesic length helpers."""
import geopandas as gpd
import numpy as np
from pyproj import Geod
GEOD = Geod(ellps='WGS84')
def assign_points(points, tracts):
    """One row per input; ties go to smallest GEOID. Preserve missing matches."""
    p = points[['geometry']].copy().reset_index(drop=True)
    p['_row'] = np.arange(len(p))
    t = tracts[['GEOID', 'geometry']].copy()
    if p.crs != t.crs:
        raise ValueError('CRS mismatch')
    joined = gpd.sjoin(p, t, how='left', predicate='intersects')
    ties = int(joined._row.duplicated().sum())
    joined = joined.sort_values(['_row', 'GEOID'], na_position='last').drop_duplicates('_row')
    ids = joined.set_index('_row').GEOID.reindex(range(len(p)))
    return ids, {'points': len(p), 'matched': int(ids.notna().sum()),
                 'unmatched': int(ids.isna().sum()), 'extra_boundary_matches': ties}
def geodesic_length(geom):
    if geom is None or geom.is_empty or geom.geom_type in ('Point','MultiPoint'):
        return 0.0
    if geom.geom_type == 'GeometryCollection':
        return sum(geodesic_length(g) for g in geom.geoms)
    return float(GEOD.geometry_length(geom))

def geodesic_lengths(geometries):
    """Vectorised ellipsoidal lengths; do not bridge disjoint multiline parts."""
    import shapely
    arr=np.asarray(geometries,dtype=object);out=np.zeros(len(arr));kind=shapely.get_type_id(arr)
    select=np.flatnonzero(kind==1)
    if len(select):
        xy,ids=shapely.get_coordinates(arr[select],return_index=True)
        if len(xy)>1:
            good=ids[1:]==ids[:-1]
            _,_,dist=GEOD.inv(xy[:-1,0][good],xy[:-1,1][good],xy[1:,0][good],xy[1:,1][good])
            out[select]=np.bincount(ids[:-1][good],weights=dist,minlength=len(select))
    select=np.flatnonzero(kind==5)
    if len(select):
        parts,parent=shapely.get_parts(arr[select],return_index=True)
        out[select]=np.bincount(parent,weights=geodesic_lengths(parts),minlength=len(select))
    for i in np.flatnonzero(kind==7):out[i]=geodesic_length(arr[i])
    return out
