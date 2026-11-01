"""Finite reset panel; caller-prescribed interfaces are not hydrology surrogates."""
import copy,json
from pathlib import Path

def layer(**kw):
    x=dict(h=.1,d=.05,p=.45,nw=0.,saxfc=.25,st=0.,yst=-888.,f=[0.,0.],sw=[.2,.3],ice=[0.,0.]);x.update(kw);return x

def cases():
    u=layer();p=layer(f=[.02,.03],ice=[.005,.0075],nw=.001)
    f=layer(f=[.05,.05],ice=[.0125,.0125],nw=.002)
    first=layer(sw=[.06,.06],st=.001,yst=.006)
    middle=layer(st=0.,yst=0.)
    last=layer(st=-888.)
    return [dict(id=n,sequence=q,layers=ls,purpose=purpose) for n,q,ls,purpose in [
        ('U-zero',1,[u,layer(st=-888.)],'Coherent unfrozen reference; prescribed depletion to zero with stable neighbor'),
        ('P-zero',1,[p,layer(st=-888.)],'Partial frost and NW; exact dry reset'),
        ('F-zero',1,[f,layer(st=-888.)],'Full frost; clearing NW while zero-support SLSW also resets'),
        ('dry-zero',1,[layer(sw=[.05,.05]),layer(st=-888.)],'Dry no-change control'),
        ('reference-plus',1,[layer(yst=.023),layer(st=-888.)],'Deliberately positive reference mismatch'),
        ('reference-minus',1,[layer(yst=.017),layer(st=-888.)],'Deliberately negative reference mismatch'),
        ('mismatch-zero',1,[layer(yst=0.),layer(st=-888.)],'Wet fine grid with zero reference; diagnostic mismatch'),
        ('mismatch-positive',1,[layer(st=2**-25,yst=0.),layer(st=-888.)],'Same mismatch with positive ST below absolute gate'),
        ('thin-zero',1,[layer(f=[.0495,.0495],ice=[.012375,.012375],nw=.00001),layer(st=-888.)],'Positive submillimeter unfrozen support; zero branch still resets it'),
        ('carry-zero-middle',1,[first,middle,last],'Diagnostic depletion exceeds available fine water; shortage crosses zero middle layer'),
        ('carry-positive-middle',1,[first,layer(st=2**-25,yst=0.),last],'Matched positive middle layer consumes incoming shortage'),
        ('clear-zero-repeat',2,[layer(f=[.00045,.00045],ice=[.0001125,.0001125],nw=.00005,st=-888.),layer(st=-888.)],'D0 clearing, prescribed ST0, two D1 calls without YST advance; repeat is not a second loss')]]
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with a.out.open('x') as stream:json.dump(cases(),stream,indent=2);stream.write('\n')
