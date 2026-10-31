"""Standalone reviewer figures for prediction distributions and disagreement."""
from pathlib import Path
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
 a=pd.read_csv(ROOT/'submissions/demographic/prediction.csv',dtype={'GEOID':str});b=pd.read_csv(ROOT/'submissions/geographic/prediction.csv',dtype={'GEOID':str})
 fig,ax=plt.subplots(1,2,figsize=(11,4))
 bins=np.linspace(0,1,41)
 c=pd.read_csv(ROOT/'submissions/conservative/prediction.csv',dtype={'GEOID':str})
 for name,d,color in [('Demographic',a,'#226b63'),('Geographic',b,'#b35a3c'),('Conservative',c,'#665485')]:ax[0].hist(d.coverage_gap_score,bins=bins,alpha=.55,label=name,color=color)
 ax[0].set_xlabel('Heuristic score (not verified coverage)');ax[0].set_ylabel('Tracts');ax[0].legend()
 ax[1].hexbin(a.coverage_gap_score,b.coverage_gap_score,gridsize=35,mincnt=1,cmap='Greens');ax[1].plot([0,1],[0,1],color='black',lw=.8);ax[1].set_xlabel('Demographic peer heuristic');ax[1].set_ylabel('Geographic peer heuristic');ax[1].set_xlim(0,1);ax[1].set_ylim(0,1)
 fig.suptitle('Candidate behaviour and disagreement — no local target labels');fig.tight_layout();fig.savefig(ROOT/'reports/candidate-behaviour.png',dpi=180);plt.close(fig)
if __name__=='__main__':main()
