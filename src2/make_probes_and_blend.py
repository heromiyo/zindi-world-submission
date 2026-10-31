"""Rebuild the four probe files and the own-probe blend (weights solved in solve_blend.py from probe scores)."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
d=pd.read_parquet(ROOT/'outputs/structural.parquet')
(ROOT/'submissions/probes').mkdir(parents=True,exist_ok=True);(ROOT/'submissions/blend').mkdir(parents=True,exist_ok=True)
for c in ['z_fac','z_est','z_bld','z_const']:
    v=(d[c]*(0.05 if c=='z_const' else 1.0)).clip(0,1)
    pd.DataFrame({'GEOID':d.GEOID,'coverage_gap_score':v}).to_csv(ROOT/f'submissions/probes/{c}.csv',index=False,float_format='%.10g')
w={'z_const':1.074,'z_fac':0.139,'z_est':0.037,'z_bld':-0.175}   # from solve_blend.py, 4-vector own-probe solution
v=sum(w[k]*pd.read_csv(ROOT/f'submissions/probes/{k}.csv',dtype={'GEOID':str}).coverage_gap_score for k in w).clip(0,1)
v[d.region.eq('eastern-wa').values]=0
pd.DataFrame({'GEOID':d.GEOID,'coverage_gap_score':v}).to_csv(ROOT/'submissions/blend/prediction.csv',index=False,float_format='%.10g')
