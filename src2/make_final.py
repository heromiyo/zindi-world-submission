"""Rebuild submissions/final/prediction.csv (EqBuune1) from cached features. Deterministic."""
import sys, json, hashlib
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0,str(Path(__file__).parent))
import evaluate as e
from experiments import fit, BLEND
from final_steps import affine, smooth, post_tert
p,prm=fit(dict(w_STSUB=1.0,w_CR=0.45,min_ref_m=100),post=post_tert)
q,ab=affine(smooth(p,0.5))
final=np.clip(.85*q+.15*BLEND,0,1)
out=pd.DataFrame({'GEOID':e.GEOID,'coverage_gap_score':final})
dest=Path(__file__).resolve().parents[1]/'submissions/final/prediction.csv'
out.to_csv(dest,index=False,float_format='%.10g')
info={'fitted_v2_params':{k:float(v) for k,v in prm.items()},'affine_a':float(ab[0]),'affine_b':float(ab[1]),'mix_stack':0.85,'mix_blend':0.15,
      'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
(dest.parent/'params.json').write_text(json.dumps(info,indent=1));print(json.dumps(info,indent=1))
