"""Moment-equation fit: y ~ sum_j a_j c_j. Each known vector v gives <v,y> = sum_j a_j <v,c_j>.
Fit on own probes only; held-out validation on public yardstick files."""
import numpy as np, pandas as pd, json, sys
import model_v2 as m, evaluate as e
roads=m.road_table();base=pd.read_parquet('../outputs/structural.parquet')
def components(prm):
    d=m.build({**dict(w_STSUB=1.0,w_CR=0.45,sigma_T=0.5,fac_scale=1,e_scale=1),**prm},roads,base)
    dT=d.T_def.to_numpy();dB=(d.building_count>0).to_numpy(float);n=dT+dB+1
    Fd=d.F_def.to_numpy();F=d.F.to_numpy();E=d.E.to_numpy()
    C={'T':dT*d.Tgap.to_numpy()/n,'F':Fd*.5*F/n,'E':((1-Fd)+.5*Fd)*E/n,'B':dB/n,'one':np.ones(len(d))}
    sc=e.SCORED
    for k in C:C[k]=np.where(sc,C[k],0.0)
    return d,C
def fit(C,keys,use=('own',),ridge=0.0):
    rows=[];rhs=[]
    for src in use:
        for v,b,r in (e.K_OWN if src=='own' else e.K_YARD).values():
            rows.append([np.mean(v*C[k][e.SCORED]) for k in keys]);rhs.append(b)
    A=np.array(rows);y=np.array(rhs);W=np.diag(1/y)   # relative-error weighting
    a=np.linalg.solve(A.T@W@W@A+ridge*np.eye(len(keys)),A.T@W@W@y);return a
if __name__=='__main__':
    d,C=components({})
    for keys in [['one','F'],['one','F','T'],['one','F','T','E'],['one','F','T','E','B']]:
        a=fit(C,keys);p=np.clip(sum(ai*C[k] for ai,k in zip(a,keys)),0,1)
        s=e.report(p,str(keys),verbose=False)
        print(keys,dict(zip(keys,a.round(3))),{k:round(float(v),4) for k,v in s.items() if k!='name'})
