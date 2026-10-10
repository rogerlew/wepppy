"""Fast input/analysis contracts; no WEPP simulations."""
from itertools import product
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import pytest

import analyze_matrix as analysis
import test_disturbed_matrix as matrix

pytestmark = pytest.mark.unit


def test_matrix_ids_preserve_historical_cases_and_add_young_forest():
    ids = set()
    for texture, severity, vegetation in product(matrix.TEXTURES, matrix.SEVERITIES, matrix.VEG_TYPES):
        key = matrix.generate_wepp_id(texture, severity, vegetation)
        assert key == analysis.generate_wepp_id(texture, severity, vegetation)
        assert analysis.wepp_id_to_params(key) == (texture, severity, vegetation)
        ids.add(key)
        if vegetation == 'young forest':
            assert key > 80
        else:
            assert key == matrix.TEXTURES.index(texture)*20 + matrix.VEG_TYPES.index(vegetation)*4 + severity + 1
    assert ids == set(range(1, 97))
    assert matrix.MANAGEMENT_FILES['young forest', 0].endswith('Young_Forest.man')
    for severity in (1, 2, 3):
        assert matrix.MANAGEMENT_FILES['young forest', severity] == matrix.MANAGEMENT_FILES['forest', severity]


@pytest.mark.parametrize('version', [None, 3])
def test_peak_reader_supports_legacy_and_v3(tmp_path, version):
    path = tmp_path/'H1.pass.dat'
    fields = [1.0]*24
    fields[9] = .2
    header = 'p1.cli\n1 2000\n100\n5 1 2 3 4 5\n0 0 0 0\n'
    event = f'{"EVENT":<8}2000 1 '+' '.join(map(str, fields))+'\n'
    path.write_text(('WEPP_PASS_COMPONENTS 3\n' if version else '')+header+event+('SRC3 2000 1 0\n' if version else ''))
    assert analysis.parse_pass_peakflow_file(path) == [analysis.PeakEvent(1, 1, .2)]
    if version:
        path.write_text(path.read_text().replace('SRC3 2000 1', 'SRC3 2000 2'))
        with pytest.raises(ValueError):
            analysis.parse_pass_peakflow_file(path)


def test_bad_ebe_and_duplicate_dates_are_not_silently_dropped(tmp_path):
    p = tmp_path/'H1.ebe.dat'
    p.write_text('header\nheader\nheader\n1 1 1 broken\n')
    with pytest.raises(ValueError):
        analysis.parse_ebe_file(p)
    event = analysis.Event(1, 1, 1, 10, 1, 2)
    with pytest.raises(ValueError):
        analysis.events_to_dict([event, event])


def test_analysis_preserves_unpaired_event_accounting():
    a = analysis.Event(1, 1, 1, 10, 1, 2)
    b = analysis.Event(2, 1, 1, 20, 3, 4)
    c = analysis.Event(3, 1, 1, 30, 5, 6)
    ub = matrix.generate_wepp_id('loam', 0, 'young forest')
    burned = matrix.generate_wepp_id('loam', 1, 'young forest')
    results = analysis.analyze_all_comparisons({ub:[a,b], burned:[a,c]}, {ub:[],burned:[]})
    assert len(results) == 1
    row = results[0]
    assert row.total_events == 1
    assert row.burned_only_events == row.unburned_only_events == 1
    assert row.full_burned_runoff == 6 and row.full_unburned_runoff == 4


def test_hourly_context_is_staged_from_committed_inputs(tmp_path):
    matrix.stage_shared_inputs(tmp_path)
    assert (tmp_path/'wepp_ui.txt').is_file()
    assert (tmp_path/'pmetpara.txt').is_file()


def test_canonical_climate_is_finite_complete_and_pinned():
    root=Path(__file__).parent/'data'
    path=root/'mckenzie_2000_2099.cli'
    identity=json.loads((root/'mckenzie_2000_2099.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==identity['climate_sha256']
    rows=[line.split() for line in path.read_text().splitlines()[15:] if line.strip()]
    assert all(len(r)==13 and all(math.isfinite(float(x)) for x in r) for r in rows)
    dates=[dt.date(int(r[2]),int(r[1]),int(r[0])) for r in rows]
    start,end=dt.date(2000,1,1),dt.date(2100,1,1)
    assert dates==[start+dt.timedelta(days=i) for i in range((end-start).days)]
    assert identity['daily_records']==len(rows)==36525


def test_historical_invalid_climate_is_rejected_before_simulation():
    from generate_climate_fixture import validate_climate
    with pytest.raises(ValueError, match='Nonfinite'):
        validate_climate(Path(__file__).parent/'data/test_climate.cli')


def test_report_preserves_reviewed_context_before_generated_tables():
    context = '# Reviewed benchmark\n\nBuild and input scope.\n'
    report = analysis.generate_full_report([], context=context)
    assert report.startswith(context.strip()+'\n\n## Test Matrix Analysis Results')
    assert 'Full-Record Totals and One-Sided Events' in report


def test_published_report_sources_and_content_are_current():
    repo = Path(__file__).resolve().parents[2]
    metadata = json.loads((Path(__file__).parent/'analysis_results_current.provenance.json').read_text())
    for relative, expected in metadata['sources'].items():
        actual = hashlib.sha256((repo/relative).read_bytes()).hexdigest()
        assert actual == expected, f'Review and refresh the canonical report: {relative} changed'
    report = Path(__file__).parent/'analysis_results_current.md'
    assert hashlib.sha256(report.read_bytes()).hexdigest() == metadata['report_sha256']
