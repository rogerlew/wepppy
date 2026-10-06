"""Validate control or pilot evidence; never launch inference automatically."""
from pathlib import Path
import json
import sys
import numpy as np
from study import ROOT, cli_rows, LANES, sha, dump

phase=sys.argv[1]
original=json.loads((ROOT/'runs/original/terminal.json').read_text())
historical=json.loads((ROOT/'acceptance/observer-parity-report.json').read_text())
for lane,key in [('ksat20','baseline-ksat20'),('ksat35','mutant-ksat35')]:
    for name,expected in historical['lanes'][key]['files'].items():
        if name not in ('H106.hbp','H106.wat.dat'):
            assert original['lanes'][lane]['outputs'][name]==expected
cross=json.loads((ROOT/'cross-host-parity.json').read_text())
assert cross['cluster_terminal_sha256']==sha(ROOT/'runs/original/terminal.json')
assert cross['all_pair_classifications_identical']
for lane in LANES:
    assert cross[lane]['water_max_abs']<2e-5
    for field,diff in cross[lane]['observer_differences'].items():
        assert diff['max_abs'] < (1e-12 if field.endswith('_m_s') else 1e-8)
expected={'cover90':3.563,'cover80':312.292,'dense':294.416}
for lane,peak in expected.items():
    assert abs(original['lanes'][lane]['focal']['1986-02-15']['production_peak_mm_h']-peak)<0.003
report={'status':'pass','historical_peak_erosion_outputs_byte_equal':True,
        'historical_1986_peaks_equal':True,'cross_host_numeric_parity':cross,
        'hbp_byte_parity':False,'hbp_scope':'retained but not consumed; watershed routing excluded'}
if phase=='pilot':
    seeds=json.loads((ROOT/'seeds.json').read_text())['pilot']
    terminals=[json.loads((ROOT/f'runs/pilot-{s:05}/terminal.json').read_text()) for s in seeds]
    assert all(r['status']=='complete' and r['climate']['fixed_columns_equal'] for r in terminals)
    repeated=json.loads((ROOT/'runs/repeat-12345/terminal.json').read_text())
    first=next(r for r in terminals if r['seed']==12345)
    assert repeated['climate']['climate_sha256']==first['climate']['climate_sha256']
    for lane in LANES:
        assert first['lanes'][lane]['outputs']==repeated['lanes'][lane]['outputs']
        assert first['lanes'][lane]['trace_sha256']==repeated['lanes'][lane]['trace_sha256']
    _,_,control=cli_rows(ROOT/'inputs/ksat20/p106.cli')
    _,_,zero=cli_rows(ROOT/'runs/pilot-00000/climate/p106.cli')
    assert np.array_equal(control,zero)
    storm_hashes=[]
    import hashlib
    for seed in seeds:
        _,_,values=cli_rows(ROOT/f'runs/pilot-{seed:05}/climate/p106.cli')
        storm_hashes.append(hashlib.sha256(values[:,4:7].tobytes()).hexdigest())
    assert len(set(storm_hashes))==5, 'pilot seed streams are not distinct'
    report.update({'pilot_conditions':5,'repeat_seed':12345,'all_five_lanes_repeat_byte_identical':True,
                   'seed0_climate_semantically_equals_original':True,
                   'unique_climates':len({r['climate']['climate_sha256'] for r in terminals}),
                   'pilot_seconds':[r['seconds'] for r in terminals],
                   'focal_flags':{r['label']:r['focal_flags'] for r in terminals}})
dump(ROOT/f'{phase}-acceptance.json',report)
print(json.dumps(report,indent=2))
