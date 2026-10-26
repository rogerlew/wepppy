"""Run once against an independent snapshot; never hydrate the source project."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

from tests.roads.roads_project import inventory, inspect_outputs

BASE = Path('/wc1/ablation/20261026_roads_wbt_flow_direction')
SOURCE = BASE / 'source'
ROOT = BASE / 'candidate'
ORIGINAL = '/wc1/runs/cl/clogging-starch'
RECOVERED = {f'roads-seg-{n:06d}' for n in (1, 20, 21, 22, 23)}
EXCLUDED = {f'roads-seg-{n:06d}' for n in (34, 35, 38, 39)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rebase(value):
    if isinstance(value, dict):
        return {k: rebase(v) for k, v in value.items()}
    if isinstance(value, list):
        return [rebase(v) for v in value]
    if isinstance(value, str):
        for prefix in (ORIGINAL, str(SOURCE)):
            if value == prefix or value.startswith(prefix + '/'):
                return str(ROOT) + value[len(prefix):]
    return value


def main():
    from wepppy.nodb.mods.roads import Roads
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
    from wepppyo3.roads_flowpath import trace_downslope_flowpath
    import wepppyo3.roads_flowpath.roads_flowpath_rust as native
    import pyarrow.parquet as pq
    import numpy as np

    assert SOURCE.is_dir() and not ROOT.exists()
    original = inventory(SOURCE, ('wepp', 'roads', 'climate', 'dem'))
    original.update({p.name: digest(p) for p in SOURCE.glob('*.nodb')})
    (BASE / 'source-inventory.json').write_text(json.dumps(original, indent=2))
    shutil.copytree(SOURCE, ROOT)
    for path in ROOT.glob('*.nodb'):
        path.write_text(json.dumps(rebase(json.loads(path.read_text()))))
    protected = inventory(ROOT, ('wepp/runs', 'wepp/output'))
    (BASE / 'baseline-inventory.json').write_text(json.dumps(protected, indent=2))
    raster = ROOT / 'dem/wbt'
    trace_evidence = []
    for number, row, col in [(1,173,498),(20,353,249),(21,353,250),(22,354,251),(23,354,252)]:
        args = [str(raster / name) for name in ('subwta.tif','flovec.tif','relief.tif')]
        kwargs = dict(channel_path=str(raster / 'netful.tif'), max_steps=20000)
        before = trace_downslope_flowpath(*args, row, col, **kwargs)
        after = trace_downslope_flowpath(*args, row, col, wbt=True, **kwargs)
        assert not before['reaches_channel'] and after['reaches_channel']
        assert after['channel_topaz_id'] == (204 if number == 1 else 154)
        trace_evidence.append(dict(segment_id=f'roads-seg-{number:06d}', before=before, after=after))
    (BASE / 'trace-evidence.json').write_text(json.dumps(trace_evidence, indent=2))
    controller = Roads.getInstance(str(ROOT))
    controller.prepare_segments()
    result = controller.run_roads_wepp()
    (BASE / 'run-summary.json').write_text(json.dumps(result, indent=2))
    assert result['status'] == 'completed'
    assert result['executed_segment_count'] == 35
    assert {x['segment_id'] for x in result['skipped_segments']} == EXCLUDED
    completed = {x['segment_id']:x for x in result['segment_execution_records'] if x['status']=='completed'}
    assert RECOVERED <= completed.keys()
    for segment in RECOVERED:
        record = completed[segment]
        assert record['trace_reaches_channel']
        assert record['topaz_id_chn_lowpoint'] == (204 if segment.endswith('000001') else 154)
        run_id = record['segment_run_id']
        assert (ROOT / f'wepp/roads/output/H{run_id}.pass.dat').stat().st_size > 0
        slope = ROOT / f'wepp/roads/runs/p{run_id}.slp'
        assert int(slope.read_text().splitlines()[1]) == 2
        assert record['buffer_length_m'] == record['trace_path_length_m']
    receipt = lifecycle.require_current(ROOT)
    table = pq.read_table(ROOT / 'wepp/roads/output/interchange/roads_segment_loss_summary.parquet')
    rows = table.to_pylist()
    assert {completed[x]['segment_run_id'] for x in RECOVERED} <= {x['segment_run_id'] for x in rows}
    assert len(rows) == 35
    assert all(x['simulation_years'] == 16 and x['modeled_area_m2'] > 0 for x in rows)
    outputs = inspect_outputs(ROOT, 'inslope_rd')
    parquet = {}
    for path in sorted((ROOT / 'wepp/roads/output/interchange').glob('*.parquet')):
        frame = pq.read_table(path).to_pandas()
        numeric = frame.select_dtypes(include=[np.number])
        assert not np.isinf(numeric.to_numpy()).any(), path.name
        parquet[path.name] = dict(rows=len(frame),sha256=digest(path))
    assert inventory(ROOT, ('wepp/runs','wepp/output')) == protected
    assert all(digest(SOURCE / name) == sha for name,sha in original.items())
    summary = dict(status='passed',native_path=native.__file__,native_sha256=digest(Path(native.__file__)),
        executed=35,skipped=sorted(EXCLUDED),recovered=sorted(RECOVERED),receipt=receipt,
        outputs=outputs,parquet=parquet,source_unchanged=True,baseline_unchanged=True,
        production_deployed=False,root=str(ROOT))
    (BASE / 'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
