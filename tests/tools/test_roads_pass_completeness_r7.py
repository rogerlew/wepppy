"""No native calls: complete zero-event histories must survive strict coverage."""
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
ART = (Path(__file__).resolve().parents[2]
       / 'docs/work-packages/20261029_roads_parameterization_program/artifacts')


@pytest.fixture
def auditor(monkeypatch):
    monkeypatch.syspath_prepend(str(ART))
    spec = importlib.util.spec_from_file_location('roads_pass_completeness_r7',
                                                 ART / 'audit_pass_completeness_r7.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepared(tmp_path, auditor, *, first_year=2000, positive=False, event=False):
    runs, output = tmp_path / 'runs', tmp_path / 'output'
    runs.mkdir()
    output.mkdir()
    (runs / 'p1.cli').write_text('frozen climate bytes for calendar fixture\n')
    first, last = date(first_year, 1, 1), date(first_year, 12, 31)
    days = (last - first).days + 1
    lines = ['WEPP_PASS_COMPONENTS 3', 'p1.cli', f'1 {first_year}',
             '1.0', '5 1e-6 1e-5 1e-4 1e-3 1e-2', '0 0 0 0']
    elements = ['ELEMENT header', 'ELEMENT units']
    for i in range(days):
        day = first + timedelta(days=i)
        if event and i == 0:
            # EVENT continuations and the required version-3 source trailer.
            lines.extend([f'EVENT   {first_year} 1 ' + ' '.join(['0'] * 12),
                          ' '.join(['0'] * 12), f'SRC3 {first_year} 1 0'])
        else:
            lines.append(f'NO EVENT {first_year} {i + 1} 0 0')
        fields = ['3', str(day.day), str(day.month), '1'] + ['0'] * 22
        fields[23] = '1.000' if positive and i == 0 else '0.000'
        elements.append(''.join(token.rjust(width) for token, width in
                                zip(fields, auditor.particles.ELEMENT_WIDTHS)))
    (output / 'H1.pass.dat').write_text('\n'.join(lines) + '\n')
    (output / 'H1.element.dat').write_text('\n'.join(elements) + '\n')
    climate = dict(first=first.isoformat(), last=last.isoformat(), days=days, years=1,
                   sha256=auditor.particles.digest(runs / 'p1.cli'))
    record_path = tmp_path / 'record.json'
    record_path.write_text(json.dumps(dict(case={'climate': 'fixture'},
        inputs={'p1.cli': climate['sha256']}, outputs={})))
    rebind(record_path, auditor)
    return record_path, climate


def rebind(record_path, auditor):
    record = json.loads(record_path.read_text())
    record['outputs'] = {p.name: auditor.particles.digest(p)
                         for p in (record_path.parent / 'output').iterdir()}
    record_path.write_text(json.dumps(record))


@pytest.mark.parametrize('first_year,days', [(1, 365), (2000, 366)])
def test_complete_zero_event_history_is_valid(tmp_path, auditor, first_year, days):
    record, climate = prepared(tmp_path, auditor, first_year=first_year)
    result = auditor.audit(record, climate)
    assert result['passed'] and result['calendar_days'] == days
    assert result['event_days'] == result['positive_terminal_days'] == 0


@pytest.mark.parametrize('keep', [3, 6, 371])
def test_truncated_pass_rejected_even_with_rebound_hash(tmp_path, auditor, keep):
    record, climate = prepared(tmp_path, auditor)
    path = tmp_path / 'output/H1.pass.dat'
    path.write_text('\n'.join(path.read_text().splitlines()[:keep]) + '\n')
    rebind(record, auditor)
    with pytest.raises(ValueError, match='header|calendar'):
        auditor.audit(record, climate)


def test_positive_terminal_day_without_event_is_reported(tmp_path, auditor):
    record, climate = prepared(tmp_path, auditor, positive=True)
    result = auditor.audit(record, climate)
    assert result['passed'] and result['positive_terminal_days'] == 1
    assert result['positive_terminal_non_event_dates'] == [dict(
        date='2000-01-01', pass_label='NO EVENT', sedleave_kg_m_token='1.000',
        runoff_mm_token='0')]


def test_positive_terminal_day_cannot_be_missing_from_pass(tmp_path, auditor):
    record, climate = prepared(tmp_path, auditor, positive=True)
    path = tmp_path / 'output/H1.pass.dat'
    lines = path.read_text().splitlines()
    del lines[6]
    path.write_text('\n'.join(lines) + '\n')
    rebind(record, auditor)
    with pytest.raises(ValueError, match='daily calendar'):
        auditor.audit(record, climate)


def test_complete_event_with_positive_terminal_day_passes_coverage(tmp_path, auditor):
    record, climate = prepared(tmp_path, auditor, positive=True, event=True)
    result = auditor.audit(record, climate)
    assert result['event_days'] == result['positive_terminal_days'] == 1
    # This certificate covers dates only; the separate particle mass auditor
    # would reject these deliberately zero EVENT masses against positive soil.


def test_sparse_element_dates_do_not_require_daily_rows(tmp_path, auditor):
    record, climate = prepared(tmp_path, auditor, positive=True, event=True)
    path = tmp_path / 'output/H1.element.dat'
    path.write_text('\n'.join(path.read_text().splitlines()[:3]) + '\n')
    rebind(record, auditor)
    result = auditor.audit(record, climate)
    assert result['positive_terminal_days'] == 1


def test_no_element_events_with_complete_zero_event_pass_is_valid(tmp_path, auditor):
    record, climate = prepared(tmp_path, auditor)
    path = tmp_path / 'output/H1.element.dat'
    path.write_text('ELEMENT header\nELEMENT units\n')
    rebind(record, auditor)
    result = auditor.audit(record, climate)
    assert result['event_days'] == result['positive_terminal_days'] == 0


@pytest.mark.parametrize('mutation', ['duplicate', 'out_of_calendar', 'missing_src3',
                                    'climate_bytes', 'output_bytes'])
def test_invalid_structure_or_binding_is_rejected(tmp_path, auditor, mutation):
    record, climate = prepared(tmp_path, auditor, event=True)
    path = tmp_path / 'output/H1.pass.dat'
    lines = path.read_text().splitlines()
    if mutation == 'duplicate':
        lines[-1] = lines[-2]
    elif mutation == 'out_of_calendar':
        lines[-1] = 'NO EVENT 2001 1 0 0'
    elif mutation == 'missing_src3':
        del lines[8]
    elif mutation == 'climate_bytes':
        (tmp_path / 'runs/p1.cli').write_text('changed')
    else:
        lines.pop()
    path.write_text('\n'.join(lines) + '\n')
    if mutation != 'output_bytes':
        rebind(record, auditor)
    with pytest.raises(ValueError):
        auditor.audit(record, climate)
