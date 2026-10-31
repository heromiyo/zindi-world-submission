"""Build local-only files, diagnostics and explicitly synthetic checks. No upload code."""
from pathlib import Path
import hashlib,json,os
os.environ.setdefault('OMP_NUM_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score
from download import REGIONS
from submission import sample,validate
from peers import predict,COUNTS,CONTEXT
ROOT=Path(__file__).resolve().parents[1]
def load_features():
    ds=[]
    for r in REGIONS:
        p=ROOT/f'data/strata/{r}/{r}-strata-tract-table.parquet'
        d=pd.read_parquet(p,columns=['GEOID',*CONTEXT]);d['GEOID']=d.GEOID.astype(str).str.zfill(11);d['region']=r
        t=gpd.read_parquet(ROOT/f'data/strata/{r}/{r}-census-tracts.parquet',columns=['GEOID','geometry']).to_crs(5070)
        t.GEOID=t.GEOID.astype(str).str.zfill(11)
        if t.geometry.isna().any() or t.geometry.is_empty.any() or not t.geometry.is_valid.all():raise ValueError('Invalid or missing tract geometry')
        cent=t.geometry.representative_point();t['x_m']=cent.x;t['y_m']=cent.y
        d=d.merge(t[['GEOID','x_m','y_m']],on='GEOID',validate='one_to_one')
        for layer in ['poi','buildings','roads']:
            f=pd.read_parquet(ROOT/f'outputs/{r}/{layer}-features.parquet');f.GEOID=f.GEOID.astype(str).str.zfill(11)
            need={'poi':['poi_count'],'buildings':['building_count'],'roads':['road_metres','highway_metres']}[layer]
            d=d.merge(f[['GEOID',*need]],on='GEOID',validate='one_to_one',how='left')
        ds.append(pd.DataFrame(d))
    joined=sample().merge(pd.concat(ds),on=['GEOID','region'],how='left',validate='one_to_one')
    required=[*CONTEXT[:2],*COUNTS,'x_m','y_m']
    if joined[required].isna().any().any():raise ValueError('Missing feature joins or required context')
    if not np.isfinite(joined[required].to_numpy(float)).all():raise ValueError('Nonfinite input')
    if (joined[COUNTS+['pop_total','ALAND']]<0).any().any():raise ValueError('Negative counts/context')
    joined['county']=joined.GEOID.str[:5]
    return joined

def export(d,pred,mode):
    dest=ROOT/'submissions'/mode;dest.mkdir(parents=True,exist_ok=True)
    result=d[['GEOID']].copy();result['coverage_gap_score']=pred['score'];validate(result)
    result.to_csv(dest/'prediction.csv',index=False,float_format='%.17g')
    diag=d[['GEOID','region','pop_total','ALAND',*COUNTS]].copy()
    for name in ['defined_proxies','neighbors','distance','zero_population']:diag[name]=pred[name]
    for n,c in enumerate(COUNTS):diag['peer_q25_'+c]=pred['expected'][:,n];diag['relative_shortfall_'+c]=pred['shortfall'][:,n]
    diag['coverage_gap_score']=pred['score'];diag['low_evidence']= (pred['neighbors']<16)|(pred['defined_proxies']<2)|pred['zero_population']
    diag.to_csv(dest/'diagnostics.csv',index=False)
    cfg={'method':mode,'k':32,'peer_quantile':.25,'seed':20261023,'runtime':'local/open-source only','unscored':True,'competition_rmse':None,'warning':'Relative peer shortfall is not an identified or calibrated reference gap. Zero population falls back to zero, without claiming completeness. All-road length is a proxy, not the hidden highway component.'}
    (dest/'config.json').write_text(json.dumps(cfg,indent=2))
    digest=hashlib.sha256((dest/'prediction.csv').read_bytes()).hexdigest()
    info={'candidate':mode,'rows':len(result),'min':float(pred['score'].min()),'mean':float(pred['score'].mean()),'p95':float(np.quantile(pred['score'],.95)),'max':float(pred['score'].max()),'low_evidence_rows':int(diag.low_evidence.sum()),'competition_rmse':None,'sha256':digest}
    (dest/'manifest.json').write_text(json.dumps(info,indent=2))
    (dest/'METHOD.md').write_text(f'''# {mode} peer-shortfall candidate\n\n**Local only, unscored, provisional.** True competition RMSE is unknown.\n\nUses only supplied Overture building bbox centres, clipped all-road geodesic lengths, POI counts and supplied population/land area/urban share. Never uses removed references, reference-derived building counts or sample labels.\n\nWithin each region, take up to32 other positive-population tracts nearest in standardized log(1+population), log(1+land km²), urban fraction and urban-missing indicator. {'Also includes projected representative-point coordinates in100km units; this favors nearby peers while retaining demographic context.' if mode=='geographic' else 'Geography is limited to region membership; peers need not be nearby.'}\n\nFor each of three observed quantities, expected count/length is the peer25th percentile. Proxy shortfall=max(0,1-observed/expected) where expected>0. Average defined proxy shortfalls equally. Undefined proxies are omitted; if none exist, or population=0, use the zero-baseline fallback. This does not reproduce organiser-defined flags/components.\n\nThe lower quartile is a conservative prior choice, not tuned against leaderboard scores. No supervised fit is possible without labels. Counts measure both true supply and mapping intensity; their effects cannot be separated here. Some complete maps may receive high scores. Proximity does not measure emergency travel time.\n\nDiagnostics include peer expectations, counts, distance and low-evidence flags. Sensitivity and synthetic county-held-out tests are in reports/. Synthetic omission detection is not target-gap validation. Building assignment is approximate and its diagnostic sample is recorded separately.\n\nSHA256: {digest}\n''')
    return info

def synthetic(d,mode):
    rows=[];all_original=[];all_dropped=[];groups=d.county.to_numpy()
    for fold,(train,test) in enumerate(GroupKFold(n_splits=5).split(d,groups=groups)):
        base=predict(d,mode,reference=train,query=test)
        altered=d[COUNTS].to_numpy(float).copy();altered[test]*=.5
        changed=predict(d,mode,reference=train,query=test,observed=altered)
        valid=(base['neighbors']>=3)&(~base['zero_population'])&(base['defined_proxies']>0)
        a=base['score'][valid];b=changed['score'][valid]
        if len(a):all_original.extend(a);all_dropped.extend(b)
        rows.append({'fold':fold,'held_out_counties':len(set(groups[test])),'rows':len(test),'eligible':int(valid.sum()),'original_mean_proxy_score':float(a.mean()) if len(a) else None,'thinned_mean_proxy_score':float(b.mean()) if len(b) else None,'mean_paired_increase':float((b-a).mean()) if len(a) else None})
        assert not set(groups[train])&set(groups[test])
        if (b+1e-12<a).any():raise ValueError('Monotonicity failed with fixed peers')
    a=np.asarray(all_original);b=np.asarray(all_dropped)
    return {'method':mode,'question':'Can a fixed peer estimator distinguish observed counts from the same areas with all three quantities synthetically halved, when reference peers exclude held-out counties?','warning':'Synthetic counts/lengths, not real missing objects or competition reference labels; AUC is not coverage-gap RMSE. No statistical independence between paired observations is assumed.','eligible_rows':len(a),'paired_detection_auc':float(roc_auc_score(np.r_[np.zeros(len(a)),np.ones(len(b))],np.r_[a,b])) if len(a) else None,'folds':rows}

def main():
    (ROOT/'reports').mkdir(exist_ok=True);d=load_features();d.to_parquet(ROOT/'outputs/tract-features.parquet',index=False)
    comparison=[];sensitivity=[];checks=[];preds={}
    baseline=ROOT/'submissions/baseline';baseline.mkdir(parents=True,exist_ok=True)
    import shutil
    shutil.copyfile(ROOT/'outputs/baseline-zero.csv',baseline/'prediction.csv')
    (baseline/'METHOD.md').write_text('# Existing zero baseline\n\nExact file previously uploaded as oEhc56z5. Public RMSE0.107246299. It is not a trained model. Preserved for comparison only; no new upload.\n')
    comparison.append({'candidate':'baseline','rows':len(d),'min':0.,'mean':0.,'p95':0.,'max':0.,'competition_rmse':.107246299,'sha256':hashlib.sha256((baseline/'prediction.csv').read_bytes()).hexdigest()})
    for mode in ['demographic','geographic']:
        p=predict(d,mode);preds[mode]=p['score'];comparison.append(export(d,p,mode));checks.append(synthetic(d,mode))
        for k,q in [(16,.25),(64,.25),(32,.1),(32,.5)]:
            v=predict(d,mode,k=k,quantile=q)['score'];sensitivity.append({'method':mode,'k':k,'quantile':q,'mean_score':float(v.mean()),'mean_abs_change':float(abs(v-p['score']).mean()),'max_abs_change':float(abs(v-p['score']).max()),'fraction_change_gt_0_1':float((abs(v-p['score'])>.1).mean())})
        print('BUILT',mode,flush=True)
    # A disclosed conservative variant; fixed prior weights, not a fitted calibration.
    dest=ROOT/'submissions/conservative';dest.mkdir(parents=True,exist_ok=True)
    result=d[['GEOID']].copy();result['coverage_gap_score']=.1*preds['demographic']+.1*preds['geographic'];validate(result)
    result.to_csv(dest/'prediction.csv',index=False,float_format='%.17g')
    digest=hashlib.sha256((dest/'prediction.csv').read_bytes()).hexdigest()
    info={'candidate':'conservative','rows':len(d),'min':float(result.coverage_gap_score.min()),'mean':float(result.coverage_gap_score.mean()),'p95':float(result.coverage_gap_score.quantile(.95)),'max':float(result.coverage_gap_score.max()),'competition_rmse':None,'sha256':digest}
    (dest/'manifest.json').write_text(json.dumps(info,indent=2));comparison.append(info)
    (dest/'config.json').write_text(json.dumps({'weights':{'baseline':.8,'demographic':.1,'geographic':.1},'competition_rmse':None,'weights_fitted':False,'disclosure':'Fixed shrinkage prior; not a third independently trained model.'},indent=2))
    (dest/'METHOD.md').write_text('# Conservative shrinkage variant\n\nLocal provisional estimate.0.8×zero baseline +0.1×demographic peer estimate +0.1×geographic peer estimate. Weights fixed before the new-method scores, not estimated from hidden labels or optimised feedback.\n\nThis downweights peer shortfall because actual supply differences may cause much of that shortfall. It is not a third independent model. It may miss genuine large gaps. Compare local disagreement/sensitivity and measured scores separately; its true RMSE remains unknown until scored. All component data and limits are inherited from the two method cards.\n')
    pd.DataFrame(comparison).to_csv(ROOT/'reports/candidate-comparison.csv',index=False)
    pd.DataFrame(sensitivity).to_csv(ROOT/'reports/sensitivity.csv',index=False)
    (ROOT/'reports/synthetic-checks.json').write_text(json.dumps(checks,indent=2))
    diff=d[['GEOID','region']].copy()
    for n,y in preds.items():diff[n]=y
    diff['absolute_difference']=abs(diff.demographic-diff.geographic);diff.sort_values('absolute_difference',ascending=False).to_csv(ROOT/'reports/candidate-disagreement.csv',index=False)
    sums=[]
    for n,y in preds.items():
        for r,g in d.assign(score=y).groupby('region'):sums.append({'method':n,'region':r,'rows':len(g),'mean':g.score.mean(),'p95':g.score.quantile(.95),'max':g.score.max()})
    pd.DataFrame(sums).to_csv(ROOT/'reports/regional-predictions.csv',index=False)
if __name__=='__main__':main()
