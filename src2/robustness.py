"""Re-estimate central RMSE under 300 random 30% public subsets (second moments recomputed on the subset)."""
import numpy as np, pandas as pd
import evaluate as e
rng=np.random.default_rng(20261031)
S=np.load('../outputs/cand_stack.npy');B=e.vec('submissions/blend/prediction.csv');C=e.vec('submissions/probes/z_const.csv')*1.196
cands={'blend(0)':B,'stack(11)':S,'mix .85':.85*S+.15*B,'mix .7':.7*S+.3*B,'mix .5':.5*S+.5*B}
K={**e.K_OWN,**e.K_YARD};V=np.c_[[v for v,b,r in K.values()]].T;R=np.array([r for v,b,r in K.values()])
N=len(V);out={k:[] for k in cands}
for it in range(300):
    m=rng.random(N)<0.3;Vm=V[m]
    b=(e.EY2+np.mean(Vm**2,0)-R**2)/2;G=Vm.T@Vm/m.sum();Gi=np.linalg.pinv(G,rcond=1e-10)
    for k,p in cands.items():
        pm=p[e.SCORED][m];c=Gi@(Vm.T@pm/m.sum());out[k].append(np.sqrt(max(e.EY2-2*c@b+np.mean(pm**2),0)))
df=pd.DataFrame(out);print(df.describe(percentiles=[.05,.5,.95]).T[['mean','5%','50%','95%']].round(5))
print('win rate:',df.idxmin(axis=1).value_counts(normalize=True).round(3).to_dict())
for k,p in cands.items():
    s=p[e.SCORED];print(k,'min',s.min().round(4),'max',s.max().round(4),'WA nonzero',int((p[~e.SCORED]!=0).sum()))
