"""Descriptive candidate spatial clustering; never a claim of bias or true error."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
ROOT=Path(__file__).resolve().parents[1]
def moran(y,neighbors):
    y=np.asarray(y,float);z=y-y.mean();den=float(z@z)
    if den==0:return None
    # Directed kNN, each row has weight1/k and zero diagonal; n/S0=1.
    return float(np.sum(z*z[neighbors].mean(axis=1))/den)
def main():
    d=pd.read_parquet(ROOT/'outputs/tract-features.parquet');rows=[]
    for mode in ['demographic','geographic']:
        scores=pd.read_csv(ROOT/f'submissions/{mode}/prediction.csv',dtype={'GEOID':str})
        f=d.merge(scores,on='GEOID',validate='one_to_one')
        for region,g in f.groupby('region',sort=True):
            xy=g[['x_m','y_m']].to_numpy(float);idx=NearestNeighbors(n_neighbors=min(9,len(g)),algorithm='brute').fit(xy).kneighbors(xy,return_distance=False)
            # Explicitly remove self, even with identical coordinates.
            nei=np.array([[j for j in row if j!=i][:8]for i,row in enumerate(idx)])
            val=moran(g.coverage_gap_score.to_numpy(),nei)
            rows.append({'method':mode,'region':region,'rows':len(g),'moran_I':val,'weights':'directed8-nearest projected representative points; self excluded, row-standardised','interpretation':'descriptive spatial structure of heuristic predictions only; not residuals, discrimination or observed coverage'})
    pd.DataFrame(rows).to_csv(ROOT/'reports/spatial-patterns.csv',index=False)
if __name__=='__main__':main()
