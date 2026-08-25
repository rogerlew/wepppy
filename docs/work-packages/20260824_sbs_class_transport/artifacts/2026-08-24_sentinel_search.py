"""Grid search for the SBS unassigned sentinel colour.

Composites over light and dark grounds at layer opacity 0.3 and 1.0, THEN
applies colour-vision simulation (the browser blends; the eye then perceives
the blended pixel). Scores each candidate by its worst-case CIEDE2000 against
all eight palette colours and against the bare basemap.
"""
import os as _os
exec(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                        '2026-08-24_cvd_lib.py')).read().split("PALETTE = {")[0])

PAL={'std unburned':'#008080','std low':'#52CCCC','std mod':'#FFE820','std high':'#A80000',
     'shf unburned':'#009E73','shf low':'#56B4E9','shf mod':'#F0E442','shf high':'#CC79A7'}
VISIONS=['normal','protanopia','deuteranopia','tritanopia']
GROUND={'light':(242,242,242),'dark':(26,26,26)}
OPACITIES=(0.3,1.0)

def comp(rgb,g,a): return tuple(round(a*rgb[i]+(1-a)*g[i]) for i in range(3))
def sim(rgb,k):
    lin=[srgb_to_lin(c) for c in rgb]
    if k!='normal': lin=matmul(CVD[k],lin)
    return tuple(lin_to_srgb(c) for c in lin)

P={}; GR={}
for v in VISIONS:
    for gn,g in GROUND.items():
        for a in OPACITIES:
            P[(v,gn,a)]={n:rgb_to_lab(sim(comp(hex2rgb(h),g,a),v)) for n,h in PAL.items()}
        GR[(v,gn)]=rgb_to_lab(sim(g,v))

def score(hexc):
    w=1e9; wp=None; c=hex2rgb(hexc)
    for v in VISIONS:
        for gn,g in GROUND.items():
            for a in OPACITIES:
                cl=rgb_to_lab(sim(comp(c,g,a),v))
                for n,pl in P[(v,gn,a)].items():
                    d=ciede2000(cl,pl)
                    if d<w: w,wp=d,(v,gn,a,n)
                d=ciede2000(cl,GR[(v,gn)])
                if d<w: w,wp=d,(v,gn,a,'BASEMAP')
    return w,wp

res=[]
for r in range(0,256,32):
    for gg in range(0,256,32):
        for b in range(0,256,32):
            h='#%02X%02X%02X'%(r,gg,b); w,wp=score(h); res.append((w,h,wp))
for h in ('#800098','#2000E0','#7F00FF','#FF00FF','#6000FF','#FF7F00','#000000','#FFFFFF'):
    w,wp=score(h); res.append((w,h,wp))
res.sort(reverse=True)
seen=set()
print("Top candidates (worst-case dE2000; higher is better)")
for w,h,wp in res:
    if h in seen: continue
    seen.add(h)
    print(f"  {h:9s} {w:6.2f}   binding {wp[0]}/{wp[1]}/a={wp[2]}/{wp[3]}")
    if len(seen)>=12: break
print("\nNamed:")
for name,h in (('selected #800098','#800098'),('blue-violet','#2000E0'),('purple','#7F00FF'),('magenta','#FF00FF'),
               ('orange','#FF7F00'),('black','#000000'),('white','#FFFFFF')):
    w,wp=score(h); print(f"  {name:18s} {h}  worst {w:6.2f}  binding {wp[0]}/{wp[1]}/a={wp[2]}/{wp[3]}")
