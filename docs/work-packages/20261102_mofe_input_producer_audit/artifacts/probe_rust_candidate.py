import hashlib, importlib.util, json
from pathlib import Path
root=Path('/workdir/wepppy/docs/work-packages/20261102_mofe_input_producer_audit/artifacts/rust_candidate_v1')
root.mkdir(exist_ok=False)
lib=Path('/workdir/wepppyo3/target/debug/libwepp_interchange_rust.so')
spec=importlib.util.spec_from_file_location('wepp_interchange_rust',lib)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
source=root/'source.slp';source.write_text('97.5\n1\n100 10\n2 100\n0, 0.1 1, 0.1\n')
observations=[]
for name,kwargs in [('zero',dict(buffer_length=0)),('negative',dict(buffer_length=-1)),('nonfinite',dict(buffer_length=float('inf'))),('normal',dict(buffer_length=15)),('equal',dict(buffer_length=100)),('overlong',dict(buffer_length=101))]:
    out=root/f'{name}.slp'
    try:
        count=m.segment_single_ofe_slope(str(source),dst_fn=str(out),apply_buffer=True,**kwargs)
    except ValueError as e:
        observations.append(dict(case=name,status='rejected',error=str(e),output_exists=out.exists()))
    else:
        observations.append(dict(case=name,status='written',count=count,content=out.read_text()))
out=root/'tiny.slp'
try:
    m.segment_single_ofe_slope_at_breakpoints(str(source),[0,0.00001,1],dst_fn=str(out))
except ValueError as e:
    observations.append(dict(case='tiny',status='rejected',error=str(e),output_exists=out.exists()))
result=dict(extension=str(lib),sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),observations=observations,scope='Isolated freshly built Python extension, not installed release; no native WEPP execution')
(root/'readback.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
