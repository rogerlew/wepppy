"""Regression coverage for scientific benchmark evidence handling."""
import importlib.util
from pathlib import Path
import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('roads_soil_benchmark', ROOT /
    'docs/work-packages/20261029_roads_soil_benchmark/artifacts/benchmark.py')
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)
DATA = ROOT/'tests/data/roads_soil_benchmark'


def test_native_detailed_loss_preserves_export_zero_and_integrates_spatial_regions():
    result = benchmark.parse_loss(DATA/'legacy-detailed.txt', 3.96)
    assert result['years'] == 2
    assert len(result['annual_export']) == 2
    assert result['sediment_export_kg_yr'] == 0
    # Three disjoint printed loss regions; neither the full profile length nor
    # the first region alone is the area of net soil loss.
    expected=(67.91*.150+(69.89-68.70)*.002+(73.06-70.68)*.001)*3.96
    assert result['spatial_net_loss_kg_yr'] == pytest.approx(expected)
    # Width must scale mass, not reported runoff depth.
    wider = benchmark.parse_loss(DATA/'legacy-detailed.txt', 7.92)
    assert wider['spatial_net_loss_kg_yr'] == pytest.approx(2*result['spatial_net_loss_kg_yr'])
    assert wider['runoff_mm_yr'] == result['runoff_mm_yr']


def test_native_zero_loss_requires_complete_profile_evidence(tmp_path):
    source = DATA/'modern-zero.txt'
    result = benchmark.parse_loss(source, 3.96)
    assert result['spatial_net_loss_kg_yr'] == result['sediment_export_kg_yr'] == 0
    broken = tmp_path/'broken.txt'
    # A missing region table must not be silently interpreted as zero.
    text = source.read_text()
    start = text.index('ANNUAL AVERAGE SUMMARIES')
    prefix, summary = text[:start], text[start:]
    summary = summary.replace('   0.61        0.000  1', '   missing-point       ', 1)
    broken.write_text(prefix+summary)
    with pytest.raises(ValueError, match='complete nonpositive profile'):
        benchmark.parse_loss(broken, 3.96)


def test_missing_year_fails_instead_of_averaging_partial_results(tmp_path):
    path = tmp_path/'missing.txt'
    text = (DATA/'legacy-detailed.txt').read_text()
    text = text.replace('HILLSLOPE 1 YEARLY SUMMARY FOR    2','REMOVED ANNUAL HEADER',1)
    path.write_text(text)
    with pytest.raises(ValueError, match='Incomplete yearly'):
        benchmark.parse_loss(path,3.96)


def test_climate_subset_rejects_missing_day(tmp_path):
    from datetime import date, timedelta
    source, target = tmp_path/'input.cli', tmp_path/'output.cli'
    lines = ['4.31\n','1 0 0\n','station\n','header\n','0 0 0 1 2000 1\n',
             'da mo year prcp\n','-- -- ---- ----\n']
    first=date(2000,1,1)
    for i in range(366):
        day=first+timedelta(days=i)
        lines.append(f'{day.day} {day.month} {day.year} 0.0\n')
    source.write_text(''.join(lines))
    assert benchmark.climate_subset(source,target,1)['days']==366
    source.write_text(''.join(lines[:-1]))
    with pytest.raises(ValueError,match='Incomplete/duplicate climate'):
        benchmark.climate_subset(source,target,1)
