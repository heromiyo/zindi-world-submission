import numpy as np, json
import evaluate as e
from experiments import score, BLEND
from experiments2 import affine, smooth, p8
log=json.load(open('../outputs/experiments-log.json'))
out={}
for lam in [0.3,0.5]:
    c=smooth(p8,lam);q,ab=affine(c);out[lam]=q
    score(f'11 tertiary+smooth{lam}+affine (a={ab[0]:.3f},b={ab[1]:.2f})',q,log)
lam=min(out,key=lambda k:e.interval(out[k])['central']);Q=out[lam]
for a in [0.5,0.7,0.85,1.0]:
    score(f'12 mix {a}*stack + {1-a:.2f}*blend',a*Q+(1-a)*BLEND,log)
np.save('../outputs/cand_stack.npy',Q);json.dump(log,open('../outputs/experiments-log.json','w'),indent=1)
