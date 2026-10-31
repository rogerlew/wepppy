"""Scientific illustration from the retained scalar failure and analytic root."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
HERE=Path(__file__).resolve().parent
receipt=json.loads((HERE/'depend-scalar-r3-result.json').read_text())
v=receipt['values_float32'];root=float(receipt['independent_root'])
x=np.linspace(v['xu'],v['xu']+.00024,800)
u=v['xu']+v['qostar'];A=v['phi']*v['b']*v['ktrato']/(1+v['phi'])
y=A+(v['du']-A)*np.exp((1+v['phi'])*np.log(u/(x+v['qostar'])))
fig,axes=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
a=axes[0];a.plot((x-v['xu'])*1e4,y,label='Independent deposition equation');a.axhline(0,color='0.5',lw=.8);a.axvline((root-v['xu'])*1e4,color='#00796b',ls='--',label='Finite interior root');a.set(xlabel='Distance from segment start (×10⁻⁴)',ylabel='Nondimensional deposition rate',title='The equation has a valid root');a.legend(fontsize=8)
a=axes[1];trials=np.array([.0600000024,1.47882164e11,1.03527757e22,7.24766e32]);a.semilogy(np.arange(1,5),trials,'o-',color='#b22222',label='Recorded legacy Newton trials');a.axhspan(v['xu'],v['xl'],color='#00796b',alpha=.18,label='Physical segment');a.axhline(root,color='#00796b',ls='--',label='Bounded fallback root');a.set(xlabel='Newton iteration',ylabel='Nondimensional position',title='The search escapes the segment',xticks=range(1,5));a.legend(fontsize=8)
fig.savefig(HERE/'depend-bounded-root.png',dpi=180)
fig.savefig(HERE/'depend-bounded-root.svg')
