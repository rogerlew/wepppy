"""Intra-palette separation baseline for SBS display colours.

Correct operation order: the browser composites the layer over the basemap,
then the eye perceives the composited pixel. Compositing therefore happens
BEFORE colour-vision simulation. An earlier revision of this script simulated
foreground and ground separately and composited afterwards, which is not
interchangeable because simulate() applies transfer functions, clipping and
8-bit rounding.
"""
import os as _os
exec(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                        '2026-08-24_cvd_lib.py')).read().split("PALETTE = {")[0])

STD={'unburned':'#008080','low':'#52CCCC','mod':'#FFE820','high':'#A80000'}
SHF={'unburned':'#009E73','low':'#56B4E9','mod':'#F0E442','high':'#CC79A7'}
VISIONS=['normal','protanopia','deuteranopia','tritanopia']
GROUND={'light':(242,242,242),'dark':(26,26,26)}
SENTINELS=['#800098','#5000A0','#800080','#2000E0','#7F00FF','#FF00FF']

def comp(rgb,g,a): return tuple(round(a*rgb[i]+(1-a)*g[i]) for i in range(3))
def sim(rgb,k):
    lin=[srgb_to_lin(c) for c in rgb]
    if k!='normal': lin=matmul(CVD[k],lin)
    return tuple(lin_to_srgb(c) for c in lin)
def disp(hexc,g,a,v): return sim(comp(hex2rgb(hexc),g,a),v)

for label,PAL in [('STANDARD (508)',STD),('SHIFTED (CVD)',SHF)]:
    print('='*70); print(label,'- intra-palette separation, composited then simulated')
    for a in (1.0,0.3):
        worst=1e9; wp=None
        for v in VISIONS:
            for gn,g in GROUND.items():
                n=list(PAL)
                for i in range(len(n)):
                    for j in range(i+1,len(n)):
                        d=ciede2000(rgb_to_lab(disp(PAL[n[i]],g,a,v)),
                                    rgb_to_lab(disp(PAL[n[j]],g,a,v)))
                        if d<worst: worst,wp=d,(v,gn,n[i],n[j])
        print(f"  alpha={a}: worst intra-palette dE2000 = {worst:6.2f}   ({wp[0]}/{wp[1]}: {wp[2]} vs {wp[3]})")

print()
print("Sentinel candidates, worst case vs all 8 palette colours and both bare basemaps:")
for hexc in SENTINELS:
    worst=1e9; wp=None
    for v in VISIONS:
        for gn,g in GROUND.items():
            for a in (0.3,1.0):
                cl=rgb_to_lab(disp(hexc,g,a,v))
                for PAL in (STD,SHF):
                    for n,h in PAL.items():
                        d=ciede2000(cl,rgb_to_lab(disp(h,g,a,v)))
                        if d<worst: worst,wp=d,f"{v}/{gn}/a{a}/{n}"
                d=ciede2000(cl,rgb_to_lab(sim(g,v)))
                if d<worst: worst,wp=d,f"{v}/{gn}/a{a}/BASEMAP"
    print(f"  {hexc}  worst dE2000 {worst:6.2f}   binding: {wp}")
