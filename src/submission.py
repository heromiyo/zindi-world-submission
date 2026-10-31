"""Validate every scored GEOID and bounded finite prediction before writing."""
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def sample():
 path=ROOT/'data/SampleSubmission.csv'
 if not path.exists():path=ROOT/'metadata/submission-membership.csv'
 d=pd.read_csv(path,dtype={'GEOID':str},usecols=['GEOID','region'])
 assert len(d)==9794 and d.GEOID.is_unique
 assert d.GEOID.str.fullmatch(r'\d{11}').all()
 return d[['GEOID','region']]
def validate(d):
 s=sample()
 if list(d.columns)!=['GEOID','coverage_gap_score']:raise ValueError('Only required columns permitted')
 if not d.GEOID.is_unique or d.GEOID.tolist()!=s.GEOID.tolist():raise ValueError('IDs must exactly match platform sample in order, with leading zeroes')
 y=d.coverage_gap_score.to_numpy(dtype=float)
 if not np.isfinite(y).all() or not ((0<=y)&(y<=1)).all():raise ValueError('Scores must be finite in [0,1]')
 return True
def write(scores,name,description):
 d=sample()[['GEOID']];d['coverage_gap_score']=np.asarray(scores,dtype=float);validate(d)
 p=ROOT/'outputs'/name;d.to_csv(p,index=False)
 meta={'file':name,'rows':len(d),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'description':description,'range':[float(d.coverage_gap_score.min()),float(d.coverage_gap_score.max())]}
 p.with_suffix('.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta));return p
if __name__=='__main__':
 write(np.zeros(len(sample())),'baseline-zero.csv','Null baseline: assume no coverage gap anywhere. Diagnostic comparator, not a trained model. No labels or leaderboard feedback used to construct it.')
