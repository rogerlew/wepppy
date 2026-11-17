"""Candidate project runs using the current-policy checked-in harness."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
from wepppy.nodb.mods.roads import Roads
from tests.roads.roads_project import validate_project
from tests.roads.unrutted_project import validate_unrutted_project
from wepp_runner.wepp_runner import get_linux_wepp_bin_role_paths


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument('label')
parser.add_argument('--design', required=True)
args = parser.parse_args()
root = Path('/wc1/runs/rq') / f'roads-quality-{args.label}-{args.design}'
assert not root.exists(), root
source = Path('/wc1/runs/mi/misty-eyed-divorcee' if args.design.startswith('unrutted') else '/wc1/runs/cl/clogging-starch')
print('SOURCE_IMPORTED', str(Path(sys.modules[Roads.__module__].__file__)), flush=True)
if args.design.startswith('unrutted'):
    result = validate_unrutted_project(source, root, fill_length_m=5. if args.design == 'unrutted-positive' else 30.)
else:
    result = validate_project(source, root, args.design)
controller = Roads.getInstance(str(root))
binaries = {str(Path(p)): digest(Path(p)) for p in get_linux_wepp_bin_role_paths(controller.wepp_instance.wepp_bin)}
artifacts = {str(p.relative_to(root)): digest(p) for p in (root/'wepp/roads').rglob('*') if p.is_file()}
(root/'validation-artifact-manifest.json').write_text(json.dumps({'native_binaries': binaries, 'artifacts': artifacts}, indent=2))
print('PROJECT_DONE', args.design, str(root), flush=True)
