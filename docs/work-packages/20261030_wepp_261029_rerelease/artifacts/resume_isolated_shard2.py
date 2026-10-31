from pathlib import Path
import importlib.util,sys,json,subprocess
root=Path('/workdir/wepppy/out/261029-r2-isolated')
p=root/'tools/run_pytest_sharded.py'
spec=importlib.util.spec_from_file_location('release_shards',p); m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
files,code,out=m._collect_selected_files(['tests','--maxfail=1']);assert code==0,out
shards=m.plan_shards(files=files,workers=4,module_timings={})
selected=shards[1]
receipt={'collected_files':len(files),'shard':2,'files':selected,'reason':'Repeat entire stopped shard without changing tests after measured 1.239s/1s HTTP timing assertion; other shards continue.'}
Path('/workdir/wepppy/out/roads-channel-accounting-20261030/isolated-shard2-selection.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(subprocess.run([sys.executable,'-m','pytest',*selected],cwd=root).returncode)
