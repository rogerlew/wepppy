from pathlib import Path
import importlib.util,sys,json,subprocess
root=Path('/workdir/wepppy/out/261029-r3-isolated')
p=root/'tools/run_pytest_sharded.py'
spec=importlib.util.spec_from_file_location('release_shards',p); m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
files,code,out=m._collect_selected_files(['tests','--maxfail=1']);assert code==0,out
shards=m.plan_shards(files=files,workers=4,module_timings={})
selected=shards[1]
start=next(i for i,p in enumerate(selected) if p.endswith('/tests/weppcloud/test_run_catalog_reader.py'))
selected=selected[start:]
receipt={'collected_files':len(files),'shard':2,'files':selected,'reason':'Repeat failed browser module and all remaining shard-2 modules with canonical installed Playwright browser path restored; /ms-playwright did not exist. Seven prior passes in repeated module counted once.'}
Path('/workdir/wepppy/docs/work-packages/20261031_wepp_261029_rerelease_r3/artifacts/application-shard2-tail-selection.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(subprocess.run([sys.executable,'-m','pytest',*selected,'--maxfail=1','--basetemp=/tmp/r3s2tail'],cwd=root).returncode)
