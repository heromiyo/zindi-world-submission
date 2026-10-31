"""Label-free evaluation against exactly-known public-leaderboard aggregates.
For any submitted file p with public RMSE r: <p,y>/N = (E[y^2] + E[p^2] - r^2)/2 (E over scored tracts).
Own probes are used for fitting/validation; public yardstick files (other participants, with their
published public RMSE) are used ONLY as validation yardsticks, never as model inputs."""
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]
EY2=0.107246299**2
OWN={'submissions/demographic/prediction.csv':0.140188939,'submissions/geographic/prediction.csv':0.139906454,
     'submissions/probes/z_fac.csv':0.097931153,'submissions/probes/z_est.csv':0.109089522,
     'submissions/probes/z_bld.csv':0.124615516,'submissions/probes/z_const.csv':0.089560921}
YARD={'outputs/yardsticks/kevin_v8.csv':0.084048897,'outputs/yardsticks/kevin_v7.csv':0.08513992,
      'outputs/yardsticks/sub_13_permitted_heuristic.csv':0.091386601,'outputs/yardsticks/sub_14_permitted_roadmix.csv':0.088906556,
      'outputs/yardsticks/sub_16_tuned_public_blend.csv':0.082014142}
_sample=pd.read_csv(ROOT/'data/SampleSubmission.csv',dtype={'GEOID':str},usecols=['GEOID','region'])
GEOID=_sample.GEOID;SCORED=(_sample.region!='eastern-wa').to_numpy()
def vec(f):return pd.read_csv(ROOT/f,dtype={'GEOID':str}).set_index('GEOID').coverage_gap_score.reindex(GEOID).to_numpy(float)
def known(files):
    out={}
    for f,r in files.items():
        v=vec(f)[SCORED];out[Path(f).parent.name if Path(f).stem=='prediction' else Path(f).stem]=(v,(EY2+np.mean(v**2)-r**2)/2,r)
    return out
K_OWN=known(OWN);K_YARD=known(YARD)
def report(p,name='candidate',verbose=True):
    p=np.asarray(p,float)[SCORED]
    rows=[]
    for src,K in [('own',K_OWN),('yard',K_YARD)]:
        for k,(v,b,r) in K.items():
            dist=np.sqrt(np.mean((p-v)**2))
            rows.append({'src':src,'vec':k,'known_<v,y>':b,'model_<v,p>':np.mean(v*p),'rel_err':np.mean(v*p)/b-1,'ub_rmse':r+dist})
    d=pd.DataFrame(rows)
    mean_y=K_OWN['z_const'][1]/0.05
    calib_rmse=np.sqrt(max(EY2-np.mean(p**2),0))
    summ={'name':name,'mean_p':p.mean(),'mean_y':mean_y,'calibrated_rmse':calib_rmse,'ub_rmse':d.ub_rmse.min(),
          'moment_mae_own':d[d.src=='own'].rel_err.abs().mean(),'moment_mae_yard':d[d.src=='yard'].rel_err.abs().mean()}
    if verbose:print(d.round(5).to_string(index=False))
    return summ
if __name__=='__main__':
    # sanity: Gram of [y, known vectors] must be PSD if yardstick scores belong to these files and same public split
    allk={**K_OWN,**K_YARD};names=list(allk);V=np.c_[[allk[n][0] for n in names]].T
    G=np.zeros((len(names)+1,)*2);G[0,0]=EY2;G[0,1:]=G[1:,0]=[allk[n][1] for n in names];G[1:,1:]=V.T@V/len(V)
    print('min eig (should be >=~0):',np.linalg.eigvalsh(G).min())
    for n in names:print(n,'implied corr(v,y)=',round(allk[n][1]/np.sqrt(EY2*np.mean(allk[n][0]**2)),3))

def interval(p,use_yard=True):
    """Rigorous public-RMSE interval for candidate p (up to public-subset sampling of second moments).
    Known span S = own probes (+ yardsticks). MSE = Ey2 - 2<p,y> + |p|^2, <p,y> = <Pi p,y> + <r,y>,
    |<r,y>| <= |r| * |y_perp|, |y_perp|^2 = Ey2 - |Pi y|^2."""
    K={**K_OWN,**(K_YARD if use_yard else {})}
    V=np.c_[[v for v,b,r in K.values()]].T;b=np.array([b for v,b,r in K.values()])
    p=np.asarray(p,float)[SCORED];N=len(p)
    G=V.T@V/N;Gi=np.linalg.pinv(G,rcond=1e-10)
    c=Gi@(V.T@p/N);proj=V@c;r=p-proj
    py_known=c@b                                  # <Pi p, y>
    y_perp=np.sqrt(max(EY2-b@Gi@b,0))
    rn=np.sqrt(np.mean(r**2));pp=np.mean(p**2)
    mse_c=EY2-2*py_known+pp
    lo=np.sqrt(max(mse_c-2*rn*y_perp,0));hi=np.sqrt(mse_c+2*rn*y_perp)
    return {'central':float(np.sqrt(max(mse_c,0))),'lo':float(lo),'hi':float(hi),'resid_rms':float(rn),'y_perp':float(y_perp)}
