"""Exploratory snapshot audit. No assertion of independently verified service closure."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from download import REGIONS
from submission import sample
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/discovery';SEED=20261023

def contrast(d):
    cells=[]
    for (region,kind),g in d.groupby(['region','facility_type'],sort=True):
        a=g[g.high_joint];b=g[~g.high_joint]
        n1,n0=len(a),len(b);c1=int(a.source_closed.sum());c0=int(b.source_closed.sum())
        cells.append({'region':region,'facility_type':kind,'n_high':n1,'closed_high':c1,'n_other':n0,'closed_other':c0,'rate_high':c1/n1 if n1 else np.nan,'rate_other':c0/n0 if n0 else np.nan,'eligible_cell':n1>=5 and n0>=5})
    tab=pd.DataFrame(cells)
    good=tab[tab.eligible_cell].copy()
    if not len(good):return None,tab
    w=(good.n_high+good.n_other);value=float(((good.rate_high-good.rate_other)*w).sum()/w.sum())
    return value,tab

def cluster_sensitivity(d,cells,reps=999):
    good=cells[cells.eligible_cell].copy();county=sorted(d.county.unique())
    if len(county)<20 or good.empty:return {'status':'not estimated: too few counties/common cells'}
    weights=(good.n_high+good.n_other).to_numpy(float);weights/=weights.sum()
    totals=np.zeros((len(county),len(good),2));closed=totals.copy();cmap={c:i for i,c in enumerate(county)}
    for j,row in enumerate(good.itertuples()):
        z=d[(d.region==row.region)&(d.facility_type==row.facility_type)]
        for (c,h),g in z.groupby(['county','high_joint']):
            totals[cmap[c],j,int(h)]=len(g);closed[cmap[c],j,int(h)]=g.source_closed.sum()
    rng=np.random.default_rng(SEED);vals=[];skipped=0
    # Resample counties within each region, keeping region representation.
    region_counties=[np.array([cmap[c] for c in sorted(g.county.unique())]) for _,g in d.groupby('region')]
    for _ in range(reps):
        ids=np.concatenate([rng.choice(a,size=len(a),replace=True)for a in region_counties]);freq=np.bincount(ids,minlength=len(county))
        n=np.tensordot(freq,totals,axes=1);c=np.tensordot(freq,closed,axes=1)
        if (n==0).any():skipped+=1;continue
        rates=c/n;vals.append(float(((rates[:,1]-rates[:,0])*weights).sum()))
    return {'status':'county-resampling sensitivity only, not uncertainty about the fixed map snapshot','seed':SEED,'requested_replicates':reps,'valid_replicates':len(vals),'skipped':skipped,'counties':len(county),'interval95':np.quantile(vals,[.025,.975]).tolist() if vals else None,'assumption':'counties sampled within fixed regions; cells and standardisation weights fixed from observed shared cells'}

def audit_queue(d):
    rng=np.random.default_rng(SEED);selected=[]
    for flag,target in [(True,40),(False,40)]:
        pool=d[d.source_closed.eq(flag)].sort_values(['region','facility_type','id']).copy();pool['_random']=rng.random(len(pool))
        picks=[]
        for _,g in pool.groupby(['region','facility_type']):picks.extend(g.sort_values('_random').head(4).index.tolist())
        picks=picks[:target]
        if len(picks)<target:
            rest=pool.loc[~pool.index.isin(picks)].sort_values('_random');picks+=rest.head(target-len(picks)).index.tolist()
        selected.append(pool.loc[picks].drop(columns='_random').assign(sample_role='source_closed' if flag else 'comparison_record'))
    q=pd.concat(selected).copy();q['review_status']='not_independently_verified';q['independent_source_url']='';q['review_decision']='';q['alternative_explanation']=''
    q.to_csv(OUT/'record-review-queue.csv',index=False)

def main():
    OUT.mkdir(parents=True,exist_ok=True);context=[];records=[];thresholds=[]
    cols=['GEOID','pop_total','pct_urban','svi_covered','svi_housing_transport','epht_covered','epht_heat_days_summer','epht_year_min','epht_year_max','epht_metric','epht_threshold']
    for r in REGIONS:
        c=pd.read_parquet(ROOT/f'data/strata/{r}/{r}-strata-tract-table.parquet',columns=cols);c.GEOID=c.GEOID.astype(str).str.zfill(11);c['region']=r
        c=sample().query('region==@r').merge(c,on=['GEOID','region'],how='left',validate='one_to_one')
        cov=c.svi_covered.eq(True)&c.epht_covered.eq(True)&c.svi_housing_transport.notna()&c.epht_heat_days_summer.notna()
        h=c.loc[cov,'epht_heat_days_summer'].quantile(.75);s=c.loc[cov,'svi_housing_transport'].quantile(.75)
        c['context_covered']=cov;c['high_joint']=cov&c.epht_heat_days_summer.ge(h)&c.svi_housing_transport.ge(s)
        thresholds.append({'region':r,'covered_tracts':int(cov.sum()),'excluded_tracts':int((~cov).sum()),'heat_q75':h,'svi_housing_transport_q75':s,'high_joint_tracts':int(c.high_joint.sum()),'definition':'upper quartiles within region among tracts covered by both sources; ties included'})
        context.append(c)
        d=pd.read_csv(ROOT/f'outputs/{r}/facility-audit.csv',dtype={'GEOID':str,'id':str});d['region']=r;records.append(d)
    allfac=pd.concat(records,ignore_index=True);c=pd.concat(context,ignore_index=True)
    em=allfac[allfac.facility_type.isin(['fire','ems'])].copy().reset_index(drop=True)
    if em.id.duplicated().any():raise ValueError('Duplicate emergency record IDs; investigate before audit')
    em=em.merge(c,on=['GEOID','region'],how='left',validate='many_to_one')
    if em.context_covered.isna().any():raise ValueError('Missing emergency-context joins')
    em['source_closed']=em.operating_status.eq('permanently_closed');em['status_unknown']=em.operating_status.isna()|em.operating_status.eq('')
    em['county']=em.GEOID.str[:5];em.to_csv(OUT/'emergency-record-evidence.csv',index=False)
    pd.DataFrame(thresholds).to_csv(OUT/'context-thresholds.csv',index=False)
    d=em[em.context_covered].copy();primary,cells=contrast(d);cells.to_csv(OUT/'primary-comparisons.csv',index=False)
    b=cluster_sensitivity(d,cells)
    known=d[d.operating_status.isin(['open','permanently_closed'])];known_effect,known_cells=contrast(known);known_cells.to_csv(OUT/'known-status-sensitivity.csv',index=False)
    regions=[]
    for r,g in d.groupby('region'):
        v,_=contrast(g);regions.append({'region':r,'records':len(g),'source_closed':int(g.source_closed.sum()),'status_unknown':int(g.status_unknown.sum()),'standardised_difference_pp':None if v is None else v*100})
    pd.DataFrame(regions).to_csv(OUT/'regional-audit.csv',index=False)
    raw=d.groupby('high_joint').agg(records=('id','size'),source_closed=('source_closed','sum'),status_unknown=('status_unknown','sum')).reset_index();raw['source_closed_rate']=raw.source_closed/raw.records;raw.to_csv(OUT/'raw-group-comparison.csv',index=False)
    flag=em[em.source_closed].copy();flag['review_status']='source record only; real-world closure unverified';flag.to_csv(OUT/'source-closed-records.csv',index=False)
    audit_queue(em)
    features=[]
    for row in flag.itertuples():features.append({'type':'Feature','geometry':{'type':'Point','coordinates':[row.lon,row.lat]},'properties':{'id':row.id,'GEOID':row.GEOID,'name':row.name,'region':row.region,'facility_type':row.facility_type,'source_status':'permanently_closed','independent_verification':False}})
    (OUT/'source-closed-records.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},indent=2))
    low,high=(b.get('interval95')or [None,None]);group_sizes=d.groupby('high_joint').size(); supports=primary is not None and primary>0 and low is not None and low>0 and len(group_sizes)==2 and group_sizes.min()>=20
    result={'primary_question':'Is the proportion of source-closed emergency POI records greater in joint upper-quartile heat and housing/transport vulnerability tracts, after service/region standardisation?','analysis_status':'exploratory, selected after earlier record screening','all_emergency_records':len(em),'source_closed':int(em.source_closed.sum()),'status_unknown':int(em.status_unknown.sum()),'eligible_context_records':len(d),'excluded_context_records':len(em)-len(d),'standardised_difference_pp':None if primary is None else primary*100,'known_status_only_difference_pp':None if known_effect is None else known_effect*100,'cluster_resampling':b,'primary_direction_supported_under_this_design':bool(supports),'independent_service_closures_verified':0}
    (OUT/'findings.json').write_text(json.dumps(result,indent=2))
    plt.rcParams.update({'font.size':10});fig,ax=plt.subplots(figsize=(8,4))
    stat=em.assign(status=em.operating_status.fillna('unknown')).groupby(['facility_type','status']).size().unstack(fill_value=0)
    stat.reindex(columns=['open','permanently_closed','unknown'],fill_value=0).plot.barh(stacked=True,ax=ax,color=['#226b63','#be4937','#b5babe']);ax.set_xlabel('Supplied POI records');ax.set_ylabel('');ax.set_title('Emergency map records: status is unknown for many entries');fig.tight_layout();fig.savefig(OUT/'status-counts.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4));p=pd.DataFrame(regions);ax.barh(p.region,p.standardised_difference_pp,color='#226b63');ax.axvline(0,color='black',lw=.8);ax.set_xlabel('High joint context minus others (percentage points)');ax.set_title('Source-closed record difference, adjusted for service mix');fig.tight_layout();fig.savefig(OUT/'regional-differences.png',dpi=170);plt.close(fig)
    fig,axs=plt.subplots(1,5,figsize=(15,4))
    for ax,r in zip(axs,REGIONS):
        f=em[em.region.eq(r)];z=flag[flag.region.eq(r)];ax.scatter(f.lon,f.lat,s=3,c='#c1cbc8',alpha=.5);ax.scatter(z.lon,z.lat,s=17,c='#be4937');ax.set_title(r);ax.set_xlabel('Longitude');ax.set_ylabel('Latitude')
    fig.suptitle('Source-reported closed records (red), not independently confirmed closures');fig.tight_layout();fig.savefig(OUT/'record-locations.png',dpi=170);plt.close(fig)
    interpretation=('The exploratory positive contrast survives the stated county-resampling sensitivity, but it is about source-reported record status and does not verify actual closure, causal harm or independent confirmation.' if supports else 'The primary positive-disparity hypothesis is not established by this design. Do not replace it with a favourable subgroup and describe that as confirmation. The snapshot still contains source-reported closed emergency records worth reviewing.')
    examples=flag.sort_values(['region','GEOID','id']).groupby('region').head(3)
    lines=['# Emergency-record discovery report','', '**Local exploratory analysis; no writeup has been submitted.**','',f'Of {len(em):,} supplied fire/EMS POI records, {int(em.source_closed.sum()):,} are explicitly marked permanently_closed. Another {int(em.status_unknown.sum()):,} have unknown status. These are observations about the supplied map snapshot, not verified closures of real services.','', '## Primary comparison','',f'Covered records: {len(d):,}; excluded for incomplete community context: {len(em)-len(d):,}. Heat means historical summertime days above a locally defined percentile of maximum heat index (2015–2023), not current weather. Region-specific cutoffs are in context-thresholds.csv. It is relative unusual-heat frequency, not an absolute cross-region temperature ranking.','',f'Region/service-standardised high-context minus comparison difference: {primary*100:.3f} percentage points.' if primary is not None else 'No common comparison cells met the minimum.',f'Known-status-only sensitivity: {known_effect*100:.3f} percentage points.' if known_effect is not None else 'Known-status sensitivity unavailable.','',interpretation,'', 'County resampling is a sensitivity/generalisation model, not a confidence statement about the exact snapshot totals. Its assumptions and interval are in findings.json. Cells require at least5 records per group; primary groups must also have at least20 records overall. Few-record cells and context exclusions limit interpretation.','', '## Named record examples — verification queue, not findings of real closure','', '| Region | GEOID | Name | Street recorded in source |','| --- | --- | --- | --- |']
    for z in examples.itertuples():lines.append(f'| {z.region} | {z.GEOID} | {str(z.name).replace(chr(124),"/")} | {str(z.address).replace(chr(124),"/")} |')
    lines+=['','## Why this could matter','', 'A map consumer that counts every emergency-category record without examining identity or status may mistake stale records for usable services. This is a plausible mechanism. We have not shown an actual dispatcher used these records, that an ambulance was delayed or that any person was harmed. Existing services may have moved, changed operators, shared dispatch contacts or stale status metadata.','', '## Reproduce and review','', 'Run src/discovery.py after the supplied-data POI extraction. All thresholds, denominators, exclusions, cell comparisons and named record IDs are exported. The80-record review queue is deliberately marked not_independently_verified; it requires evidence before any stronger assertion. No additional source data were used. Data provenance and fixed-seed decisions are in metadata/ and preparation/IMPLEMENTATION-DECISIONS.md.','', 'Files: emergency-record-evidence.csv; source-closed-records.csv/.geojson; raw-group-comparison.csv; primary-comparisons.csv; known-status-sensitivity.csv; context-thresholds.csv; record-review-queue.csv; findings.json.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
