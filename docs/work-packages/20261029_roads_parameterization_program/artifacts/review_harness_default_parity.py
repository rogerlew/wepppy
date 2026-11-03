import hashlib,json,subprocess,sys,tempfile,types
from pathlib import Path
from tests.roads import roads_matrix as current
from wepppy.nodb.mods.roads import Roads
old=types.ModuleType('roads_matrix_old_review')
old.__file__=current.__file__
sys.modules[old.__name__]=old
source=subprocess.check_output(['git','show','e0308765c:tests/roads/roads_matrix.py'],text=True)
exec(compile(source,old.__file__,'exec'),old.__dict__)
root=Path(tempfile.mkdtemp(prefix='roads-default-parity-review-'))
rows=[]
for arrangement in ('bare_direct','rutted','unrutted_three'):
    cases={}
    for name,module in [('old',old),('current',current)]:
        path=root/arrangement/name
        path.mkdir(parents=True)
        module.initialize(path)
        roads=Roads(str(path),'disturbed9002-wbt-mofe.cfg')
        record=module.prepare(roads,path,module.Case('median','loam','gravel','low',arrangement),1)
        cases[name]={'inputs':record['input_sha256'],'emitted':record['emitted'],'requested':record['requested'],'parity':record['parity']}
    assert cases['old']==cases['current'],arrangement
    rows.append({'arrangement':arrangement,'identical':True,'evidence':cases['current']})
result={'starting_revision':'e0308765c','current_matrix_sha256':hashlib.sha256(Path(current.__file__).read_bytes()).hexdigest(),'root':str(root),'rows':rows,'native_calls':0}
path=Path('/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts/revised-harness-default-parity.json')
with path.open('x') as f: json.dump(result,f,indent=2); f.write('\n')
print(json.dumps({'passed':True,'contexts':len(rows),'native_calls':0,'receipt':str(path)}))
