"""Declared fresh native project controls for a behavior-preserving refactor."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import traceback

from wepppy.nodb.mods.roads import Roads
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
from tests.roads.roads_project import validate_project, inspect_outputs
from wepp_runner.wepp_runner import get_linux_wepp_bin_role_paths


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory(root):
    paths=list(root.glob('*.nodb'))
    for folder in ('wepp/runs','wepp/output','roads','climate'):
        paths.extend(p for p in (root/folder).rglob('*') if p.is_file())
    return {str(p.relative_to(root)):digest(p) for p in sorted(set(paths))}


def rebase(value,source,root):
    if isinstance(value,dict): return {k:rebase(v,source,root) for k,v in value.items()}
    if isinstance(value,list): return [rebase(v,source,root) for v in value]
    if isinstance(value,str) and (value==str(source) or value.startswith(str(source)+'/')):
        return str(root)+value[len(str(source)):]
    return value


def run_unrutted(source, root, fill):
    before=inventory(source)
    assert not root.exists()
    shutil.copytree(source,root,ignore=shutil.ignore_patterns('_query_engine','_logs','export','*.log'))
    for path in root.glob('*.nodb'):
        path.write_text(json.dumps(rebase(json.loads(path.read_text()),source,root)))
    (root/'validation-source-before.json').write_text(json.dumps(before,indent=2))
    baseline={str(p.relative_to(root)):digest(p) for folder in ('wepp/runs','wepp/output') for p in (root/folder).rglob('*') if p.is_file()}
    payload=json.loads((root/'roads/roads.uploaded.geojson').read_text())
    for feature in payload['features']:
        feature['properties'].update(DESIGN='outslope_unrutted', FILL_LENGTH_M=fill,FILL_SLOPE_PCT=10.,BUFFER_LENGTH_M=30.,BUFFER_SLOPE_PCT=10.)
    upload=root/'validation-input.geojson';upload.write_text(json.dumps(payload))
    declaration={'source':str(source),'synthetic_inputs':{'fill_length_m':fill,'fill_slope_pct':10.,'buffer_length_m':30.,'buffer_slope_pct':10.},'source_upload_sha256':before['roads/roads.uploaded.geojson'],'input_sha256':digest(upload),'input_feature_count':len(payload['features']),'excluded_features':[], 'purpose':'geometry/code parity, not site prediction'}
    (root/'validation-declaration.json').write_text(json.dumps(declaration,indent=2))
    roads=Roads.getInstance(str(root));roads.set_uploaded_geojson(str(upload)); prepared=roads.prepare_segments()
    (root/'validation-prepared.json').write_text(json.dumps(prepared,indent=2))
    try:
        result=roads.run_roads_wepp()
    except RuntimeError as exc:
        if fill != 30.: raise
        result=roads._last_run_summary
        assert result['status']=='failed'
        assert any(row.get('reason')=='failed_road_fill_exceeds_hillslope' for row in result['segment_execution_records']),result
        assert not lifecycle.available(root)
        (root/'validation-expected-error.txt').write_text(str(exc))
    else:
        assert fill==5. and result['status']=='completed'
        lifecycle.require_current(root)
        (root/'validation-accounting.json').write_text(json.dumps(inspect_outputs(root,'outslope_unrutted'),indent=2))
    finally:
        (root/'validation-result.json').write_text(json.dumps(roads._last_run_summary,indent=2))
        assert before==inventory(source),'source inventory changed'
        assert baseline=={str(p.relative_to(root)):digest(p) for folder in ('wepp/runs','wepp/output') for p in (root/folder).rglob('*') if p.is_file()},'baseline changed'
    return result


parser=argparse.ArgumentParser();parser.add_argument('label');parser.add_argument('--design',required=True);args=parser.parse_args()
base=Path('/wc1/runs/rq')
base.mkdir(exist_ok=True)
root=base/f'roads-quality-{args.label}-{args.design}'
assert not root.exists(),root
source=Path('/wc1/runs/mi/misty-eyed-divorcee' if args.design.startswith('unrutted') else '/wc1/runs/cl/clogging-starch')
print('SOURCE_IMPORTED',str(Path(sys.modules[Roads.__module__].__file__)),flush=True)
if args.design.startswith('unrutted'):
    result=run_unrutted(source,root,5. if args.design=='unrutted-positive' else 30.)
else:
    result=validate_project(source,root,args.design)
controller=Roads.getInstance(str(root))
binaries={str(Path(p)):digest(Path(p)) for p in get_linux_wepp_bin_role_paths(controller.wepp_instance.wepp_bin)}
artifacts={str(p.relative_to(root)):digest(p) for p in (root/'wepp/roads').rglob('*') if p.is_file()}
(root/'validation-artifact-manifest.json').write_text(json.dumps({'native_binaries':binaries,'artifacts':artifacts},indent=2))
print('PROJECT_DONE',args.design,str(root),flush=True)
