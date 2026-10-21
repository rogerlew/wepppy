from pathlib import Path
import re,subprocess,json
root=Path('/workdir/wepppy/docs/work-packages/20261021_wepp_261021_release/artifacts')
failed='tests/nodb/test_project_config_builder_snapshot.py'
modules=[]
for line in (root/'wepppy-sanity-remainder.log').read_text().splitlines():
 m=re.match(r'^(tests/\S+\.py) ',line)
 if m:
  if m[1]==failed:break
  if m[1] not in modules:modules.append(m[1])
assert len(modules)>200
excluded=modules+['tests/disturbed/test_disturbed_matrix.py','tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py']
all_modules=subprocess.check_output(['rg','--files','tests'],cwd='/workdir/wepppy',text=True).splitlines()
remaining=sorted(p for p in all_modules if re.fullmatch(r'(test_.*|.*_test)\.py',Path(p).name) and p not in excluded)
assert len(remaining)==404,len(remaining)
args=['wctl','run-pytest',*remaining,'--maxfail=1']
(root/'resumed-suite-coverage.json').write_text(json.dumps({'completed_modules':modules,'excluded_completed_matrices':excluded[-2:],'resume_at':failed,'remaining_modules':remaining,'command':args},indent=2)+'\n')
with (root/'wepppy-sanity-resumed.log').open('w') as log:
 proc=subprocess.run(args,cwd='/workdir/wepppy',stdout=log,stderr=subprocess.STDOUT)
print('resumed suite exit',proc.returncode)
raise SystemExit(proc.returncode)
