"""Regenerate only the disposable acceptance baseline from its existing climate."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
os.environ['WEPPPY_NCPU'] = '4'
from wepppy.nodb.core import Wepp
from wepppy.nodb.mods.omni.omni import _post_watershed_run_cleanup
from wepppy.wepp.interchange import run_wepp_hillslope_interchange
from wepppy.climates.cligen import ClimateFile

wd = Path('/wc1/runs/qa/qa-omni-reload-20261116')
artifacts = Path('/workdir/wepppy/docs/work-packages/20261116_omni_sbs_reload/artifacts')
out = artifacts / 'fixture_repair.json'
assert not out.exists(), 'Preserve prior attempts'
backup = wd / 'fixture_repair_before'
backup.mkdir()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
# Hash source inputs without loading or mutating source NoDb controllers.
source = Path('/wc1/runs/th/thespian-cleanness')
source_files = [*source.glob('*.nodb'), *source.glob('climate/*.cli'), *source.glob('wepp/runs/*.cli')]
source_before = {str(p.relative_to(source)): digest(p) for p in source_files}
for pattern in ('*.cli', '*.run', '*.err'):
    for p in (wd / 'wepp/runs').glob(pattern):
        shutil.copy2(p, backup / p.name)
result = {'status': 'running', 'runid': wd.name, 'uid': os.getuid(), 'gid': os.getgid(),
          'backup': str(backup), 'before': {p.name: digest(p) for p in backup.iterdir()}}
def record():
    out.write_text(json.dumps(result, indent=2)+'\n')
record()
wepp = Wepp.getInstance(str(wd))
started = time.time()
wepp.prep_hillslopes(max_workers=4)
translator = wepp.watershed_instance.translator_factory()
verified = []
for topaz_id in wepp.watershed_instance._subs_summary:
    src = wd / 'climate' / wepp.climate_instance.sub_summary(topaz_id)['cli_fn']
    prepared = wd / 'wepp/runs' / ('p%s.cli' % translator.wepp(top=int(topaz_id)))
    assert digest(src) == digest(prepared), prepared
    years = sorted(set(int(y) for y in ClimateFile(str(prepared)).as_dataframe()['year']))
    assert years == list(range(2007, 2025)), (prepared, years)
    verified.append({'file': prepared.name, 'source': src.name, 'sha256': digest(prepared), 'years': years})
result['climates'] = verified
record()
wepp.run_hillslopes(max_workers=4)
run_wepp_hillslope_interchange(wepp.output_dir, pass_family=wepp.pass_family,
                             start_year=2007, delete_after_interchange=False)
wepp.prep_watershed()
wepp.run_watershed()
_post_watershed_run_cleanup(wepp)
assert source_before == {str(p.relative_to(source)): digest(p) for p in source_files}
result.update(status='passed', source_unchanged=True, seconds=time.time()-started,
              fresh_hillslope_outputs=len([p for p in (wd/'wepp/output').glob('H*.loss.dat') if p.stat().st_mtime >= started]))
record()
print('FIXTURE_BASELINE_PASS', result['fresh_hillslope_outputs'], flush=True)
