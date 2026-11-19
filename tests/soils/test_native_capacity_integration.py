"""Actual source factory, SSURGO writer, preparation and multi-OFE capacity."""
import json
from pathlib import Path
import sqlite3

import pytest
from wepppy.soils.ssurgo.ssurgo import SurgoCollectionWorkerViewFactory, WeppSoil
from wepppy.wepp.soils.horizon_boundary import validate_soil_horizon_capacity
from wepppy.wepp.soils.utils import WeppSoilUtil, SoilMultipleOfeSynth

pytestmark = pytest.mark.unit


def puaulu():
    data=json.loads((Path(__file__).parent/'fixtures/puaulu_capacity/source.json').read_text())
    conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
    for table in ('component','chorizon','chfrags','chtexturegrp','corestrictions'):
        rows=data[table]
        keys=list(rows[0]) if rows else ['cokey','reskind']
        conn.execute(f"CREATE TABLE {table} ({','.join(keys)})")
        conn.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in keys)})",[[row[k] for k in keys] for row in rows])
    view=SurgoCollectionWorkerViewFactory(conn=conn).build({2372202},data['source'])
    conn.close()
    return WeppSoil(view,2372202,horizon_defaults=dict(sandtotal_r=66.8,claytotal_r=7,om_r=7,cec7_r=11.3,sandvf_r=10,smr=55.5))


@pytest.mark.parametrize('version',['7778','2006.2'])
def test_actual_ssurgo_write_capacity_and_preserved_failure(tmp_path,version):
    soil=puaulu()
    assert len(soil.horizons)==22 and soil.num_layers==20
    target=tmp_path/'2372202.sol';target.write_text('prior artifact')
    with pytest.raises(ValueError,match='10-layer limit'):
        soil.write(str(tmp_path),version=version)
    assert target.read_text()=='prior artifact'
    soil.write(str(tmp_path),version=version,max_horizons=23)
    validate_soil_horizon_capacity(target.read_text(),max_horizons=23)
    parsed=WeppSoilUtil(str(target))
    assert parsed.obj['ofes'][0]['nsl']==21
    depths=[h['solthk'] for h in parsed.obj['ofes'][0]['horizons']]
    assert depths[:4]==[80,200,220,300] and depths[-1]==1400


def test_real_disturbed_and_spawn_argument_preparation(tmp_path):
    from wepppy.nodb.core.wepp import prep_soil
    from wepppy.nodb.mods.disturbed.disturbed import _build_disturbed_mofe_soil
    puaulu().write(str(tmp_path),max_horizons=23)
    source=tmp_path/'2372202.sol'
    treated=tmp_path/'treated.sol'
    _build_disturbed_mofe_soil(dict(source_soil_path=str(source),output_path=str(treated),
        disturbed_mukey='puaulu',desc='Puaulu',meta_fn=None,sol_ver=9002.0,
        replacements={},recompute_wp_fc_using_rosetta_on_bd_override=False,max_horizons=23))
    prepared=tmp_path/'prepared.sol'
    prep_soil(('1',str(treated),str(prepared),None,None,.75,False,1800,False,1000,False,23))
    assert WeppSoilUtil(str(prepared)).obj['ofes'][0]['nsl']==21
    merged=tmp_path/'multi.sol'
    SoilMultipleOfeSynth([str(prepared)]*2,max_horizons=23).write(str(merged))
    validate_soil_horizon_capacity(merged.read_text(),max_horizons=23)
    assert [o['nsl'] for o in WeppSoilUtil(str(merged)).obj['ofes']]==[21,21]
    before=prepared.read_bytes()
    with pytest.raises(ValueError,match='10-layer limit'):
        prep_soil(('1',str(treated),str(prepared),None,None,.75,False,1800,False,1000,False,10))
    assert prepared.read_bytes()==before


def test_general_restrictive_conductivity_preserves_large_profile(tmp_path):
    from wepppy.wepp.soils.utils.utils import modify_kslast
    puaulu().write(str(tmp_path), max_horizons=23)
    source = tmp_path / "2372202.sol"
    destination = tmp_path / "modified.sol"
    destination.write_text("prior artifact")
    with pytest.raises(ValueError, match="10-layer limit"):
        modify_kslast(str(source), str(destination), .02)
    assert destination.read_text() == "prior artifact"
    modify_kslast(str(source), str(destination), .02, max_horizons=23)
    before = WeppSoilUtil(str(source)).obj["ofes"][0]["horizons"]
    after = WeppSoilUtil(str(destination)).obj["ofes"][0]["horizons"]
    assert before == after and len(after) == 21


@pytest.mark.parametrize('version', [7778.0, 9002.0])
@pytest.mark.parametrize('summary_type', ['summary', 'detached'])
def test_treatment_writer_preserves_puaulu_horizons(tmp_path, version, summary_type):
    import logging
    from types import SimpleNamespace
    from wepppy.nodb.mods.treatments.treatments import Treatments
    from wepppy.nodb.core.soils import SoilSummary
    from wepppy.wepp.soils.utils import simple_texture

    puaulu().write(str(tmp_path), max_horizons=23)
    source = tmp_path / '2372202.sol'
    parsed = WeppSoilUtil(str(source))
    summary = SoilSummary(mukey='2372202', fname=source.name,
                          soils_dir=str(tmp_path), desc='Puaulu', build_date='validation')
    if summary_type == 'detached':
        summary = SimpleNamespace(fname=source.name, clay=parsed.clay, sand=parsed.sand,
                                  desc='Puaulu', meta_fn=None)
    soils = SimpleNamespace(soils_dir=str(tmp_path), soil_input_capacity=23,
                            soils={'2372202': summary}, domsoil_d={'101': '2372202'},
                            islocked=lambda: True)
    landuse = SimpleNamespace(domlc_d={'101': 'forest'},
                             managements={'forest': SimpleNamespace(disturbed_class='forest')})
    texture = simple_texture(clay=parsed.clay, sand=parsed.sand)
    disturbed = SimpleNamespace(sol_ver=version,
                                land_soil_replacements_d={(texture, 'forest'): {}})
    treatments = Treatments.__new__(Treatments)
    treatments.wd = str(tmp_path)
    treatments.logger = logging.getLogger('capacity-treatment')
    treatments._modify_soil(landuse, soils, disturbed, '101')
    result = tmp_path / soils.soils[soils.domsoil_d['101']].fname
    validate_soil_horizon_capacity(result.read_text(), max_horizons=23)
    actual = WeppSoilUtil(str(result)).obj['ofes'][0]['horizons']
    expected = parsed.obj['ofes'][0]['horizons']
    assert len(actual) == 21
    assert [h['solthk'] for h in actual] == [h['solthk'] for h in expected]


def test_location_writer_preserves_puaulu_horizons(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from wepppy.nodb.mods.locations import location_mixin as module

    puaulu().write(str(tmp_path), max_horizons=23)
    (tmp_path / 'lc_soiltype_map.json').write_text('{}')
    summary = SimpleNamespace(mukey='2372202', fname='2372202.sol', area=1)
    soils = SimpleNamespace(soils_dir=str(tmp_path), soil_input_capacity=23,
                            soils={'2372202': summary}, domsoil_d={'101': '2372202'},
                            locked=nullcontext)
    monkeypatch.setattr(module.Soils, 'getInstance', lambda wd: soils)
    monkeypatch.setattr(module.Landuse, 'getInstance', lambda wd: SimpleNamespace(domlc_d={'101': 'forest'}))
    monkeypatch.setattr(module.Watershed, 'getInstance', lambda wd: SimpleNamespace(
        hillslope_area=lambda top: 1, wsarea=1))
    monkeypatch.setattr(module, 'read_lc_file', lambda path: {('forest', 'forest'): {}})
    location = SimpleNamespace(data_dir=str(tmp_path), wd=str(tmp_path),
                               default_wepp_type='forest', lc_lookup_fn='lookup.csv',
                               _nodb='general.nodb')
    module.LocationMixin.modify_soils(location)
    result = tmp_path / soils.soils[soils.domsoil_d['101']].fname
    validate_soil_horizon_capacity(result.read_text(), max_horizons=23)
    actual = WeppSoilUtil(str(result)).obj['ofes'][0]['horizons']
    expected = WeppSoilUtil(str(tmp_path / '2372202.sol')).obj['ofes'][0]['horizons']
    assert len(actual) == 21
    assert [h['solthk'] for h in actual] == [h['solthk'] for h in expected]


def test_ag_fields_synthesis_preserves_puaulu_horizons(tmp_path):
    import shutil
    from wepppy.nodb.mods.ag_fields.concept1_inputs import synthesize_concept1_parent_inputs

    parent = tmp_path / 'parent'
    parent.mkdir()
    puaulu().write(str(parent), max_horizons=23)
    (parent / '2372202.sol').rename(parent / 'p1.sol')
    fixtures = Path(__file__).parents[1] / 'wepp_runner/fixtures/hillslope_smoke/runs'
    for suffix in ('slp', 'man', 'cli'):
        shutil.copy2(fixtures / f'p1.{suffix}', parent / f'p1.{suffix}')
    rows = [dict(parent_wepp_id=1, ofe_id=index + 1,
                 normalized_start=start, normalized_end=end,
                 source_kind='background', sub_field_id=None)
            for index, (start, end) in enumerate(((0, .5), (.5, 1)))]
    target = tmp_path / 'target'
    synthesize_concept1_parent_inputs(parent_wepp_id=1, ofe_rows=rows,
        parent_runs_dir=parent, subfield_runs_dir=tmp_path / 'unused',
        target_runs_dir=target, target_width_m=10, max_horizons=23)
    result = target / 'p1.sol'
    validate_soil_horizon_capacity(result.read_text(), max_horizons=23)
    ofes = WeppSoilUtil(str(result)).obj['ofes']
    assert [ofe['nsl'] for ofe in ofes] == [21, 21]
    expected = WeppSoilUtil(str(parent / 'p1.sol')).obj['ofes'][0]['horizons']
    assert all(ofe['horizons'] == expected for ofe in ofes)
