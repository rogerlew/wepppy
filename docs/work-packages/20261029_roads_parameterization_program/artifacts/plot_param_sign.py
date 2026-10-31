"""Illustrate the observed PARAM sign error; not a model prediction curve."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
x=np.linspace(0,1,1001)
slope=np.where(x<=.05,-19.5121956*x+1.95121956,.975609779)
old=slope*(x-1)/.001
new=slope*(x-1)/-.001
fig,ax=plt.subplots(1,2,figsize=(10,3.8),constrained_layout=True)
ax[0].plot(x,old,color='#b44',label='Old zero guard: +0.001')
ax[0].plot(x,new,color='#16734a',label='U12 zero guard: −0.001')
ax[0].axhline(0,color='0.4',lw=.7)
ax[0].set(xlabel='Normalized OFE distance',ylabel='Normalized raw transport capacity',title='Observed positive-slope geometry')
ax[0].legend(fontsize=8)
t=np.geomspace(1e-10,1e-3,1000)
r=np.float32(1)/np.float32(np.float32(t)-np.float32(1))
d=np.float32(r+np.float32(1))
ax[1].semilogx(t,t/(t-1),label='Exact t / (t − 1)',color='0.2')
ax[1].semilogx(t,np.where(abs(d)<.001,np.where(d>=0,.001,-.001),d),label='Old guarded REAL',color='#b44')
ax[1].semilogx(t,np.where(abs(d)<.001,np.where(d>0,.001,-.001),d),label='U12 guarded REAL',color='#16734a',ls='--')
ax[1].set(xlabel='Positive continuity quantity t',ylabel='Coefficient denominator',title='Rounding erases the limiting sign')
ax[1].legend(fontsize=8)
fig.suptitle('PARAM: repair the sign of the existing bound',fontsize=12)
for suffix in ['png','svg','pdf']:fig.savefig(HERE/f'param-denominator-sign.{suffix}',dpi=180)
