"""Broaden actual project-runtime sensitivity before selecting a soil treatment."""
from concurrent.futures import ProcessPoolExecutor
import importlib.util
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('roads_runtime_diagnostic', HERE/'runtime_diagnostic.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
d.ROOT = d.ROOT.parent/'project-runtime-screen-v2'


def execute(task):
    # Multiprocessing must pickle this importable entry point, not the helper
    # loaded under a transient importlib module name.
    return d.execute(task)


def main():
    source_declaration = json.loads((d.SOURCE/'declaration.json').read_text())
    cases = [c for c in source_declaration['cases'] if c['variant'] in ('roles','erosion','rock')]
    tasks = [('-'.join(c.values()), 'project') for c in cases]
    d.ROOT.mkdir(exist_ok=False)
    (d.ROOT/'matrix-v1').mkdir(); (d.ROOT/'analysis/cases').mkdir(parents=True)
    (d.ROOT/'inputs').symlink_to(d.SOURCE/'inputs', target_is_directory=True)
    d.b.dump(d.ROOT/'declaration.json', dict(tasks=tasks, binary=source_declaration['binary'],
        sidecars={p.name:d.b.digest(p) for p in d.SHARED.iterdir() if p.is_file()},
        source_declaration_sha256=d.b.digest(d.SOURCE/'declaration.json'),
        script_sha256=d.b.digest(Path(__file__)), executor_sha256=d.b.digest(Path(d.__file__)),
        auditor_sha256=d.b.digest(Path(d.a.__file__)),
        purpose='288-case full-project-runtime sensitivity for the three non-fixed-conductivity treatments',
        rationale='Isolate production-runtime omissions before changing generated subsurface material or selecting parameters',
        limits='Same existing project PMET/snow/GW settings applied explicitly across three climates; this is a controlled model-setting panel, not regional calibration, held-out validation or actual project-builder validation'))
    shutil.copy2(__file__, d.ROOT/'executed-project-runtime-screen.py')
    shutil.copy2(d.__file__, d.ROOT/'executed-runtime-diagnostic.py')
    results=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for index,result in enumerate(pool.map(execute,tasks),1):
            results.append(result)
            d.b.dump(d.ROOT/'partial-results.json',results)
            print(index,len(tasks),result['case'],result['status'],flush=True)
    d.b.dump(d.ROOT/'results.json',results)
    d.b.dump(HERE/'project-runtime-screen.json',results)


if __name__ == '__main__':
    main()
