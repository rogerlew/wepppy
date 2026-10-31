"""Repeat the entire unchanged shard after a bounded fake-deploy timing failure."""
from pathlib import Path
import importlib.util,sys,json,subprocess
ROOT=Path('/workdir/wepppy/out/261029-r3-isolated')
p=ROOT/'tools/run_pytest_sharded.py'
spec=importlib.util.spec_from_file_location('release_shards',p);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
files,code,out=module._collect_selected_files(['tests','--maxfail=1']);assert code==0,out
shards=module.plan_shards(files=files,workers=4,module_timings={});selected=shards[2]
assert any(p.endswith('/tests/scripts/test_deploy_production_execution.py') for p in selected)
receipt=dict(collected_files=len(files),shard=3,files=selected,reason='Repeat whole unchanged shard after fake deployment renewal test returned timeout124 during parallel execution. No source, fixture, timing assertion or test change. Initial failed attempt retained and excluded from completed coverage. First replay used an overlong basetemp for AF_UNIX sockets; retained and excluded. Second replay uses /tmp/r3s3 without changing tests.')
Path('/workdir/wepppy/docs/work-packages/20261031_wepp_261029_rerelease_r3/artifacts/application-shard3-selection.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(subprocess.run([sys.executable,'-m','pytest',*selected,'--maxfail=1','--basetemp=/tmp/r3s3'],cwd=ROOT).returncode)
