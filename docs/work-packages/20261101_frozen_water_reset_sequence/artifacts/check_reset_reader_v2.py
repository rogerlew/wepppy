"""Controls for reset semantics, precision and explicit invalid-state retention."""
import copy,json
from pathlib import Path
from audit_resets_v2 import decompose, observe_branch

def layer():
    return dict(dg=.125,dry=.0625,ul=.04,st=0.,yst=.03125,frzw=0.,frozen=0.,soilw=.0390625,nw=0.,saxfc=.25,n=2,available=1,
                fine={1:dict(f=0.,sw=.25,ice=0.,u=.0625),2:dict(f=0.,sw=.375,ice=0.,u=.0625)})
def main(out):
    out.mkdir(parents=True,exist_ok=False);a=layer();b=copy.deepcopy(a)
    for f in b['fine'].values():f['sw']=a['dry']
    coherent=decompose(a,b);assert abs(coherent['nominal_residual_m'])<1e-16
    a['yst']+=.00390625;b['yst']=a['yst'];positive=decompose(a,b);assert abs(positive['inherited_reference_mismatch_m']-.00390625)<1e-16
    a['yst']-=.0078125;b['yst']=a['yst'];negative=decompose(a,b);assert abs(negative['inherited_reference_mismatch_m']+.00390625)<1e-16
    rejected={}
    for name,change in [('wrong_dry',lambda x:x['fine'][1].update(sw=.06)),('ice_mutation',lambda x:x['fine'][1].update(ice=.001)),('support_mutation',lambda x:x['fine'][1].update(u=.04)),('uncleared_nw',lambda x:x.update(nw=.001)),('changed_yst',lambda x:x.update(yst=1.)),('unavailable',lambda x:x.update(available=0))]:
        bad=copy.deepcopy(b);change(bad)
        try:decompose(a,bad)
        except ValueError as e:rejected[name]=str(e)
        else:raise AssertionError(name)
    # A temporally inconsistent coarse ice reference remains visible, not filtered out.
    a['frzw']=b['frzw']=-.001;flagged=decompose(a,b);assert flagged['negative_coarse_component']
    cell_bad=copy.deepcopy(a);cell_bad['fine'][1]['sw']=-.125
    assert decompose(cell_bad,b)['negative_fine_cell']
    geometry=copy.deepcopy(a);geometry['fine'][1]['u']=-.01
    geometry_after=copy.deepcopy(b);geometry_after['fine'][1]['u']=-.01
    assert decompose(geometry,geometry_after)['invalid_geometry']
    nan=copy.deepcopy(a);nan['fine'][1]['sw']=float('nan')
    try:decompose(nan,b)
    except ValueError:rejected['nonfinite']=True
    else:raise AssertionError('NaN accepted')
    pre=dict(map=1,year=1,day=1,ofe=1,hour=1,mode=1,nsl=1,parent=1,epoch=1)
    def target():return dict(pre=pre,zero=set(),requests=set(),unavailable=set())
    event=dict(pre,tag='D1_ZERO',other=[('B',1,0,[])])
    t=target();observe_branch(t,event)
    try:observe_branch(t,event)
    except ValueError:rejected['duplicate_branch']=True
    else:raise AssertionError('duplicate accepted')
    for key in ('map','year','day','ofe','hour','mode','nsl','parent','epoch'):
        bad=dict(event);bad[key]+=1
        try:observe_branch(target(),bad)
        except ValueError:rejected['branch_'+key]=True
        else:raise AssertionError(key)
    receipt=dict(passed=True,coherent=coherent,signed_mismatch=[positive,negative],rejected=rejected,negative_coordinate_retained=True)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('reset reader controls passed')
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);main(p.parse_args().out)
