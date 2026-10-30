"""Explain every nonnegative accounting discrepancy in the road-cap screen."""
from concurrent.futures import ProcessPoolExecutor
import importlib.util
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('export_gate_observer',HERE/'trace_export_gate.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
SOURCE=t.BASE/'engineered-surface-screen-v1'
ROOT=t.BASE/'engineered-accounting-v1'


def execute(name):return dict(name=name,**t.trace(SOURCE/'matrix-v1'/name,ROOT/name))


def main():
    rows=json.loads((SOURCE/'results.json').read_text())
    names=['-'.join(r['case'].values()) for r in rows if r['case']['variant']=='erosion_road_cap'
           and r['status']=='completed' and not r['negative_fluxes']
           and (not r['report_reconciled'] or r['ebe_mismatch_events'])]
    if len(names)!=4:raise ValueError('Changed accounting case set')
    ROOT.mkdir(exist_ok=False)
    t.dump(ROOT/'declaration.json',dict(cases=names,source_results_sha256=t.digest(SOURCE/'results.json'),
                                      script_sha256=t.digest(Path(__file__)),observer_sha256=t.digest(Path(t.__file__))))
    shutil.copy2(__file__,ROOT/'executed-trace-engineered-accounting.py')
    shutil.copy2(t.__file__,ROOT/'executed-trace-export-gate.py')
    with ProcessPoolExecutor(max_workers=4) as pool:results=list(pool.map(execute,names))
    t.dump(ROOT/'results.json',results);t.dump(HERE/'engineered-accounting.json',results)
    for r in results:print(r['name'],r['source_explained'],len(r['events']),r['residual_kg_yr'])


if __name__=='__main__':main()
