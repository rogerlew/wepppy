import math

def hex2rgb(h):
    h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))

def srgb_to_lin(c):
    c=c/255.0
    return c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4

def lin_to_srgb(c):
    c=max(0.0,min(1.0,c))
    v=12.92*c if c<=0.0031308 else 1.055*(c**(1/2.4))-0.055
    return max(0,min(255,round(v*255)))

def matmul(M,v):
    return [sum(M[r][k]*v[k] for k in range(3)) for r in range(3)]

# Machado, Oliveira & Fernandes (2009), severity 1.0, applied to LINEAR rgb
CVD = {
 'protanopia': [[0.152286,1.052583,-0.204868],
                [0.114503,0.786281,0.099216],
                [-0.003882,-0.048116,1.051998]],
 'deuteranopia':[[0.367322,0.860646,-0.227968],
                 [0.280085,0.672501,0.047413],
                 [-0.011820,0.042940,0.968881]],
 'tritanopia': [[1.255528,-0.076749,-0.178779],
                [-0.078411,0.930809,0.147602],
                [0.004733,0.691367,0.303900]],
}

def simulate(hexc, kind):
    r,g,b = hex2rgb(hexc)
    lin=[srgb_to_lin(r),srgb_to_lin(g),srgb_to_lin(b)]
    if kind!='normal':
        lin=matmul(CVD[kind],lin)
    return tuple(lin_to_srgb(c) for c in lin)

def rgb_to_lab(rgb):
    R,G,B=[srgb_to_lin(c) for c in rgb]
    X = 0.4124564*R+0.3575761*G+0.1804375*B
    Y = 0.2126729*R+0.7151522*G+0.0721750*B
    Z = 0.0193339*R+0.1191920*G+0.9503041*B
    Xn,Yn,Zn = 0.95047,1.00000,1.08883
    def f(t):
        return t**(1/3) if t>(6/29)**3 else t/(3*(6/29)**2)+4/29
    fx,fy,fz=f(X/Xn),f(Y/Yn),f(Z/Zn)
    return (116*fy-16, 500*(fx-fy), 200*(fy-fz))

def ciede2000(lab1,lab2):
    L1,a1,b1=lab1; L2,a2,b2=lab2
    kL=kC=kH=1.0
    C1=math.hypot(a1,b1); C2=math.hypot(a2,b2)
    Cb=(C1+C2)/2
    G=0.5*(1-math.sqrt(Cb**7/(Cb**7+25.0**7))) if Cb>0 else 0.5*(1-0)
    a1p=(1+G)*a1; a2p=(1+G)*a2
    C1p=math.hypot(a1p,b1); C2p=math.hypot(a2p,b2)
    def hp(ap,b):
        if ap==0 and b==0: return 0.0
        h=math.degrees(math.atan2(b,ap))
        return h+360 if h<0 else h
    h1p=hp(a1p,b1); h2p=hp(a2p,b2)
    dLp=L2-L1; dCp=C2p-C1p
    if C1p*C2p==0: dhp=0.0
    else:
        d=h2p-h1p
        if d>180: d-=360
        elif d<-180: d+=360
        dhp=d
    dHp=2*math.sqrt(C1p*C2p)*math.sin(math.radians(dhp/2))
    Lbp=(L1+L2)/2; Cbp=(C1p+C2p)/2
    if C1p*C2p==0: hbp=h1p+h2p
    else:
        if abs(h1p-h2p)>180: hbp=(h1p+h2p+360)/2 if (h1p+h2p)<360 else (h1p+h2p-360)/2
        else: hbp=(h1p+h2p)/2
    T=(1-0.17*math.cos(math.radians(hbp-30))+0.24*math.cos(math.radians(2*hbp))
       +0.32*math.cos(math.radians(3*hbp+6))-0.20*math.cos(math.radians(4*hbp-63)))
    dtheta=30*math.exp(-(((hbp-275)/25)**2))
    Rc=2*math.sqrt(Cbp**7/(Cbp**7+25.0**7)) if Cbp>0 else 0.0
    Sl=1+(0.015*(Lbp-50)**2)/math.sqrt(20+(Lbp-50)**2)
    Sc=1+0.045*Cbp; Sh=1+0.015*Cbp*T
    Rt=-math.sin(math.radians(2*dtheta))*Rc
    return math.sqrt((dLp/(kL*Sl))**2+(dCp/(kC*Sc))**2+(dHp/(kH*Sh))**2
                     +Rt*(dCp/(kC*Sc))*(dHp/(kH*Sh)))

PALETTE = {
 'std unburned':'#008080','std low':'#52CCCC','std mod':'#FFE820','std high':'#A80000',
 'shf unburned':'#009E73','shf low':'#56B4E9','shf mod':'#F0E442','shf high':'#CC79A7',
}
CANDIDATES = {'magenta':'#FF00FF'}

for kind in ['normal','protanopia','deuteranopia','tritanopia']:
    print('='*66); print(kind.upper())
    for cname,chex in CANDIDATES.items():
        csim=simulate(chex,kind); clab=rgb_to_lab(csim)
        rows=[]
        for pname,phex in PALETTE.items():
            psim=simulate(phex,kind)
            d=ciede2000(clab,rgb_to_lab(psim))
            rows.append((d,pname,psim))
        rows.sort()
        print(f"  {cname} {chex} -> sim rgb{csim}")
        for d,pname,psim in rows:
            flag='  <-- CONFUSABLE' if d<15 else ('  <- close' if d<25 else '')
            print(f"    dE2000 {d:6.2f}  vs {pname:14s} sim rgb{str(psim):18s}{flag}")
