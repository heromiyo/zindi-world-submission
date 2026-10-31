"""Audit artifacts, memberships, source hashes and reproducibility. No external calls."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from download import REGIONS
from submission import sample,validate
ROOT=Path(__file__).resolve().parents[1]
def main():
    checks=[]
    def record(name,passed,detail):
        checks.append({'check':name,'passed':bool(passed),'detail':detail})
    s=sample();record('sample_membership',len(s)==9794 and s.GEOID.is_unique,s.groupby('region').size().to_dict())
    for meta in json.loads((ROOT/'metadata/download-manifest.json').read_text()):
        p=ROOT/'data'/meta['path'];digest=hashlib.sha256(p.read_bytes()).hexdigest();record('source_hash:'+meta['path'],digest==meta['sha256'],digest)
    for r in REGIONS:
        diag=json.loads((ROOT/f'outputs/{r}/spatial-diagnostics.json').read_text());record('POI_conservation:'+r,diag['input_pois']==diag['matched_pois']+diag['outside_tracts'],diag)
        for layer in ['poi','buildings','roads']:
            d=pd.read_parquet(ROOT/f'outputs/{r}/{layer}-features.parquet');scored=set(s[s.region.eq(r)].GEOID)
            source_ids=set(pd.read_parquet(ROOT/f'data/strata/{r}/{r}-census-tracts.parquet',columns=['GEOID']).GEOID.astype(str).str.zfill(11))
            record('tract_membership:'+r+':'+layer,d.GEOID.is_unique and set(d.GEOID)==source_ids and scored<=set(d.GEOID),{'intermediate_rows':len(d),'scored_rows':len(scored),'unscored_extras_excluded_by_sample_join':sorted(set(d.GEOID)-scored)})
        n=json.loads((ROOT/f'outputs/{r}/network-diagnostics.json').read_text())
        for source in n['sources']:
            h=hashlib.sha256((ROOT/source['projected_cache']).read_bytes()).hexdigest();record('projected_input_hash:'+source['projected_cache'],h==source['sha256'],h)
        btab=pd.read_parquet(ROOT/f'outputs/{r}/buildings-features.parquet');record('building_conservation:'+r,int(btab.building_count.sum())+n['buildings']['unmatched']==n['buildings']['rows'],n['buildings'])
        road=n['roads'];record('road_conservation:'+r,road['assigned_metres']<=road['input_metres']+max(.1,road['input_metres']*1e-6),road)
        b=n['building_approximation_check'];record('building_approximation_documented:'+r,bool(b['groups']),b)
    for mode in ['baseline','demographic','geographic','conservative']:
        p=ROOT/f'submissions/{mode}/prediction.csv';d=pd.read_csv(p,dtype={'GEOID':str});validate(d);record('submission_integrity:'+mode,True,{'rows':len(d),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    f=pd.read_parquet(ROOT/'outputs/tract-features.parquet');record('zero_population_policy_documented',True,{'zero_population_rows':int(f.pop_total.le(0).sum()),'urban_share_missing':int(f.pct_urban.isna().sum()),'policy':'zero score fallback for zero population; urban share imputed0.5 with explicit missing indicator; no claim of complete coverage'})
    from peers import predict
    for mode in ['demographic','geographic']:
        y=predict(f,mode)['score'];expected=pd.DataFrame({'GEOID':f.GEOID,'coverage_gap_score':y}).to_csv(index=False,float_format='%.17g').encode();actual=(ROOT/f'submissions/{mode}/prediction.csv').read_bytes()
        record('second_prediction_run_hash:'+mode,hashlib.sha256(expected).digest()==hashlib.sha256(actual).digest(),hashlib.sha256(expected).hexdigest())
    a=predict(f,'demographic')['score'];b=predict(f,'geographic')['score']
    expected=pd.DataFrame({'GEOID':f.GEOID,'coverage_gap_score':.1*a+.1*b}).to_csv(index=False,float_format='%.17g').encode()
    actual=(ROOT/'submissions/conservative/prediction.csv').read_bytes();record('second_prediction_run_hash:conservative',hashlib.sha256(expected).digest()==hashlib.sha256(actual).digest(),hashlib.sha256(expected).hexdigest())
    (ROOT/'reports/validation.json').write_text(json.dumps(checks,indent=2))
    lines=['# Local validation','',f'{sum(c["passed"]for c in checks)}/{len(checks)} checks passed.','', 'These checks establish file integrity, provenance and repeatability; they do not establish true competition accuracy.','', '| Check | Result |','| --- | --- |']
    lines +=[f'| {x["check"]} | {"PASS"if x["passed"]else "FAIL"} |'for x in checks]
    lines+=['','Building centres remain approximate. See sampled disagreement details in regional network diagnostics; a small sample is not exhaustive certification. Road lengths use the WGS84 ellipsoid after tract clipping; duplicated boundary pieces are allocated once. Snapshot closure status is not independently verified.','', 'Unit tests cover boundary ties/unmatched points, CRS mismatch, geodesic units, leading-zero/ID corruption, missing/nonfinite/out-of-range scores, peer self-exclusion, zero population and synthetic monotonicity. See unit-tests.txt.']
    (ROOT/'reports/validation.md').write_text('\n'.join(lines)+'\n')
    if not all(c['passed']for c in checks):raise ValueError('Validation failed; do not upload')
    print(f'{len(checks)} local checks passed')
if __name__=='__main__':main()
