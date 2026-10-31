"""Transparent peer-shortfall heuristics, not supervised target prediction."""
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
COUNTS=['building_count','road_metres','poi_count']
CONTEXT=['pop_total','ALAND','pct_urban']
def context(d):
    p=np.log1p(d.pop_total.clip(lower=0).to_numpy(float))
    a=np.log1p(d.ALAND.clip(lower=0).to_numpy(float)/1e6)
    u=d.pct_urban.to_numpy(float)
    if np.any((u[np.isfinite(u)]<0)|(u[np.isfinite(u)]>1)):raise ValueError('Urban share must be a fraction in [0,1]')
    return np.column_stack([p,a,np.nan_to_num(u,nan=.5),np.isnan(u).astype(float)])
def predict(d,mode='demographic',reference=None,query=None,k=32,quantile=.25,observed=None):
    if mode not in ('demographic','geographic'):raise ValueError(mode)
    reference=np.arange(len(d)) if reference is None else np.asarray(reference)
    query=np.arange(len(d)) if query is None else np.asarray(query)
    reference_counts=d[COUNTS].to_numpy(float)
    counts=reference_counts if observed is None else np.asarray(observed,float)
    geoids=d.GEOID.to_numpy()
    x=context(d);expected=np.full((len(query),3),np.nan);neighbors=np.zeros(len(query),int);distance=np.full(len(query),np.nan)
    for region in sorted(d.region.unique()):
        train=reference[(d.region.to_numpy()[reference]==region)&(d.pop_total.to_numpy()[reference]>0)]
        qpos=np.flatnonzero(d.region.to_numpy()[query]==region);q=query[qpos]
        if len(train)<4:continue
        scaler=StandardScaler().fit(x[train]);a=scaler.transform(x[train]);b=scaler.transform(x[q])
        if mode=='geographic':
            #100km units; use projected coordinates only as proximity/context, not road length.
            geo=d[['x_m','y_m']].to_numpy(float)/100000.
            a=np.column_stack([a,geo[train]]);b=np.column_stack([b,geo[q]])
        model=NearestNeighbors(n_neighbors=min(k+1,len(train)),algorithm='brute',metric='euclidean',n_jobs=1).fit(a)
        dist,idx=model.kneighbors(b)
        for n,(row,ds,is_) in enumerate(zip(q,dist,idx)):
            ids=train[is_];keep=ids!=row;ids=ids[keep];ds=ds[keep]
            order=np.lexsort((geoids[ids],ds));ids=ids[order][:k];ds=ds[order][:k]
            if len(ids)<3:continue
            expected[qpos[n]]=np.quantile(reference_counts[ids],quantile,axis=0)
            neighbors[qpos[n]]=len(ids);distance[qpos[n]]=float(ds[-1])
    actual=counts[query]
    defined=np.isfinite(expected)&(expected>0)
    shortfall=np.zeros_like(actual)
    np.divide(actual,expected,out=shortfall,where=defined)
    shortfall=np.where(defined,np.maximum(0.,1.-shortfall),np.nan)
    score=np.divide(np.nansum(shortfall,axis=1),defined.sum(axis=1),out=np.zeros(len(query)),where=defined.sum(axis=1)>0)
    zero=d.pop_total.to_numpy()[query]<=0;score[zero]=0
    return {'score':np.clip(score,0.,1.),'expected':expected,'shortfall':shortfall,'defined_proxies':defined.sum(axis=1),'neighbors':neighbors,'distance':distance,'zero_population':zero}
