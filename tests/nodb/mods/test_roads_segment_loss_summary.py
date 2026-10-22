"""Real native geometry, DuckDB reduction and Parquet publication regressions."""
import json
import os
from pathlib import Path
import stat

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.nodb.mods.roads import _segment_loss_summary as summary

pytestmark = pytest.mark.integration


def _sources(root, *, second_ofes=(100.,), design="inslope_rd"):
    folder = root / summary.OUTPUT
    folder.mkdir(parents=True)
    manifest = root / summary.MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps([dict(segment_id=f"road-{i}", segment_run_id=i,
        target_hillslope_wepp_id=1, design=design if i == 902 else "inslope_rd") for i in (901, 902)]))
    passes, water = [], []
    for source, ofes, multiplier in [(901, (100.,), 1.), (902, second_ofes, 3.)]:
        index = 0
        for year in (2001, 2002):
            for day in range(1, 366):
                index += 1
                dates = dict(year=year, julian=day, month=1, day_of_month=1,
                             water_year=year, sim_day_index=index)
                event = multiplier if year == 2001 and day == 1 else 0.
                passes.append(dict(wepp_id=source, **dates, runvol=event*10, sbrunv=event*2,
                    gwbfv=event*4, tdet=event*8, tdep=event*2,
                    **{f"sedcon_{i}": .1 if event else 0. for i in range(1, 6)}))
                for ofe, area in enumerate(ofes, 1):
                    water.append(dict(wepp_id=source, ofe_id=ofe, **dates, Area=area,
                                      Q=event, latqcc=0.))
    pq.write_table(pa.Table.from_pylist(passes), folder / "H.pass.parquet")
    pq.write_table(pa.Table.from_pylist(water), folder / "H.wat.parquet")
    # Poison target-hillslope output. It must never influence source summaries.
    pq.write_table(pa.table({"wepp_id": [1], "Sediment Yield": [999999.]}), folder / "loss_pw0.hill.parquet")
    return folder


def _build(root, **kwargs):
    return root / summary.build_segment_loss_summary(root, root/summary.OUTPUT,
        expected_years=kwargs.get("expected_years", 2), start_year=kwargs.get("start_year", 2001))


def _rewrite(path, edit):
    rows = pq.read_table(path).to_pylist()
    edit(rows)
    pq.write_table(pa.Table.from_pylist(rows), path)


def test_source_identity_zero_event_year_and_original_column_order(tmp_path):
    _sources(tmp_path)
    table = pq.read_table(_build(tmp_path))
    rows = {r['segment_run_id']: r for r in table.to_pylist()}
    assert rows[901]['sediment_yield_kg'] == 2.5
    assert rows[902]['sediment_yield_kg'] == 7.5
    assert rows[901]['runoff_volume_m3'] == 5.
    assert rows[901]['subrunoff_volume_m3'] == 1.
    assert rows[901]['baseflow_volume_m3'] == 2.
    assert rows[901]['soil_loss_kg'] == 4.
    assert rows[901]['sediment_deposition_kg'] == 1.
    assert rows[901]['runoff_depth_mm'] == 50.
    assert rows[901]['road_prism_erosion_kg'] == 4.
    assert rows[901]['sediment_leaving_buffer_kg'] is None
    assert {r['loss_match_key'] for r in rows.values()} == {'segment_run_id'}
    assert not any(r['loss_row_missing'] for r in rows.values())
    assert json.loads(table.schema.metadata[b'source_sha256']).keys() == {
        str(summary.MANIFEST), str(summary.OUTPUT/'H.pass.parquet'), str(summary.OUTPUT/'H.wat.parquet')}
    assert table.schema.names == summary.SCHEMA.names
    assert not list((tmp_path/summary.OUTPUT).glob('*.pending-*'))


@pytest.mark.parametrize(('ofes','design','scope'), [((50.,150.),'outslope_rutted','mixed_profile'),
    ((200.,),'outslope_unrutted_remainder','replacement_remainder'), ((100.,),'','unclassified_profile')])
def test_full_profile_area_and_unavailable_aliases(tmp_path, ofes, design, scope):
    _sources(tmp_path, second_ofes=ofes, design=design)
    row = pq.read_table(_build(tmp_path)).to_pylist()[0]
    assert row['segment_run_id'] == 902
    assert row['modeled_area_m2'] == sum(ofes)
    assert row['profile_scope'] == scope
    assert row['road_prism_erosion_kg'] is None
    assert row['sediment_leaving_buffer_kg'] is None
    assert row['sediment_yield_density_kg_m2'] == 7.5 / sum(ofes)


@pytest.mark.parametrize('records', [[], [{'status':'skipped'}], [{'status':'failed'}]])
def test_empty_without_sources_or_calendar(tmp_path, records):
    manifest = tmp_path/summary.MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(records))
    table = pq.read_table(_build(tmp_path, expected_years=None, start_year=None))
    assert table.num_rows == 0
    assert table.schema.remove_metadata() == summary.SCHEMA


@pytest.mark.parametrize('mutation,match', [
    ('missing_id','Missing Roads PASS'), ('missing_day','calendar'), ('missing_year','simulation years'),
    ('duplicate_day','calendar'), ('null','metric'), ('nan','metric'), ('inf','metric'),
    ('calendar_mismatch','calendars'), ('overflow','Nonfinite')])
def test_invalid_sources_preserve_old_summary(tmp_path, mutation, match):
    folder = _sources(tmp_path)
    path = _build(tmp_path)
    old = path.read_bytes()
    def edit(rows):
        if mutation == 'missing_id': rows[:] = [r for r in rows if r['wepp_id'] != 902]
        elif mutation == 'missing_day': rows.pop(2)
        elif mutation == 'missing_year': rows[:] = [r for r in rows if r['year'] == 2001]
        elif mutation == 'duplicate_day': rows.append(rows[0].copy())
        elif mutation == 'calendar_mismatch': rows[0]['water_year'] += 1
        elif mutation == 'overflow': rows[0]['runvol'] = rows[0]['sedcon_1'] = 1e308
        else: rows[0]['runvol'] = {'null':None, 'nan':float('nan'), 'inf':float('inf')}[mutation]
    _rewrite(folder/'H.pass.parquet', edit)
    with pytest.raises(ValueError, match=match): _build(tmp_path)
    assert path.read_bytes() == old


@pytest.mark.parametrize('kind', ['not_list','unknown_status','duplicate','collision'])
def test_invalid_manifest_preserves_old_summary(tmp_path, kind):
    _sources(tmp_path); output = _build(tmp_path); old = output.read_bytes()
    manifest = tmp_path/summary.MANIFEST
    records = json.loads(manifest.read_text())
    if kind == 'not_list': records = {}
    elif kind == 'unknown_status': records[0]['status'] = 'unknown'
    elif kind == 'duplicate': records.append(records[0])
    else: records[0]['segment_run_id'] = 1
    manifest.write_text(json.dumps(records))
    with pytest.raises(ValueError): _build(tmp_path)
    assert output.read_bytes() == old


def test_modes_failed_candidate_and_retry(tmp_path, monkeypatch):
    _sources(tmp_path)
    old_umask = os.umask(0o007)
    try: output = _build(tmp_path)
    finally: os.umask(old_umask)
    assert stat.S_IMODE(output.stat().st_mode) == 0o660
    output.chmod(0o640); old = output.read_bytes()
    real_replace = summary.os.replace
    with monkeypatch.context() as m:
        def fail(*args): raise OSError('injected publication failure')
        m.setattr(summary.os, 'replace', fail)
        with pytest.raises(RuntimeError, match='inspect candidate'): _build(tmp_path)
    assert output.read_bytes() == old
    candidates = list(output.parent.glob('*.pending-*'))
    assert len(candidates) == 1 and pq.read_table(candidates[0]).num_rows == 2
    _build(tmp_path)
    assert stat.S_IMODE(output.stat().st_mode) == 0o640
    assert candidates[0].exists()


@pytest.mark.parametrize('source', ['manifest','pass','wat'])
def test_source_drift_after_read_preserves_old(tmp_path, monkeypatch, source):
    folder = _sources(tmp_path); output = _build(tmp_path); old = output.read_bytes()
    original = summary._summarize
    def drift(*args):
        result = original(*args)
        path = tmp_path/summary.MANIFEST if source == 'manifest' else folder/f'H.{source}.parquet'
        with path.open('ab') as stream: stream.write(b'\n')
        return result
    monkeypatch.setattr(summary, '_summarize', drift)
    with pytest.raises(ValueError, match='source changed'): _build(tmp_path)
    assert output.read_bytes() == old


def test_output_alias_cannot_modify_baseline(tmp_path):
    _sources(tmp_path)
    baseline = tmp_path/'baseline.parquet'; baseline.write_bytes(b'baseline')
    (tmp_path/summary.OUTPUT/'roads_segment_loss_summary.parquet').symlink_to(baseline)
    with pytest.raises(ValueError, match='alias'): _build(tmp_path)
    assert baseline.read_bytes() == b'baseline'


def test_legacy_start_and_status_and_zero_detachment(tmp_path):
    folder = _sources(tmp_path)
    _rewrite(folder/'H.pass.parquet', lambda rows: [row.update(tdet=0.) for row in rows])
    table = pq.read_table(_build(tmp_path, start_year=None))
    assert table['sediment_delivery_ratio'].to_pylist() == [None,None]


@pytest.mark.parametrize('records', [[], [{'status':'skipped'}], [{'status':'failed'}]])
def test_actual_facade_empty_without_model_or_climate_state(tmp_path, records):
    from wepppy.nodb.mods.roads import Roads
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    manifest = tmp_path/summary.MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(records))
    result = controller._build_roads_segment_loss_summary_parquet(interchange_dir=tmp_path/summary.OUTPUT)
    assert pq.read_table(tmp_path/result).num_rows == 0
    assert not (tmp_path/'wepp.nodb').exists()
    assert not (tmp_path/'climate.nodb').exists()
