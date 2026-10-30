"""Exercise direct serializers with deterministic source data, without downloads."""
from types import SimpleNamespace
import shlex

import pytest

from wepppy.wepp.soils.horizon_boundary import ensure_200mm_boundary
from wepppy.wepp.soils.utils import WeppSoilUtil

pytestmark = pytest.mark.unit


def horizon_records(text):
    records = [line for line in text.splitlines() if line.strip() and not line.startswith('#')]
    header = shlex.split(records[3])
    count = int(header[2])
    rows = [line.split() for line in records[4:4 + count]]
    assert len(records) == 5 + count  # Header records + horizons + restrictive record.
    assert ensure_200mm_boundary(text) == text
    return rows


def test_isric_generated_artifact_splits_crossing_material(tmp_path, monkeypatch):
    from wepppy.locales.earth.soils.isric import ISRICSoilData, isric_depths
    builder = ISRICSoilData(str(tmp_path))
    data = dict(cfvo=10, cec=15, clay=20, sand=50, silt=30,
                bdod=1.4, soc=2, wv0033=30, wv1500=15)
    monkeypatch.setattr(builder, 'extract_soil_data', lambda *_: {
        depth: dict(data) for depth in isric_depths})
    monkeypatch.setattr(builder, 'get_wrb', lambda *_: 'Cambisols')
    builder.build_soil(0, 0, soil_fn='generated.sol')
    artifact = tmp_path / 'generated.sol'
    soil = WeppSoilUtil(str(artifact))
    assert [h['solthk'] for h in soil.obj['ofes'][0]['horizons']] == [50, 150, 200, 300, 600, 1000, 2000]
    rows = horizon_records(artifact.read_text())
    assert rows[2][1:] == rows[3][1:]


def test_sift_mineral_and_water_serialization_boundaries(monkeypatch):
    from wepppy.locales.canada.bc.soils.sift.sift import SiftSoil

    class Horizon:
        valid = True
        is_organic = False
        soil_name = 'Example soil'
        simple_texture = 'loam'
        interrill, rill, shear, om, ksat = 400000, .0001, 2, 2, 8

        def __init__(self, depth):
            self.depth = depth

        def __str__(self):
            return f'{self.depth} 1.4 8 10 .30 .15 50 20 2 15 10'

    soil = SiftSoil([Horizon(150), Horizon(400)])
    monkeypatch.setattr(soil, 'summary', lambda: '# deterministic source')
    # This checks boundary output only: the legacy mineral header's missing
    # saturation field is a pre-existing, separately recorded validity issue.
    rows = horizon_records(str(soil))
    assert [float(row[0]) for row in rows] == [150, 200, 400]
    assert rows[1][1:] == rows[2][1:]
    water = horizon_records(soil._water())
    assert [float(row[0]) for row in water] == [200, 210]
    assert water[0][1:] == water[1][1:]


def test_asris_all_three_outputs_have_correct_counts_and_boundaries(tmp_path, monkeypatch):
    from wepppy.au.soils import soil_build as module
    values = {
        'Clay Content Topsoil %': 20, 'Silt Content Topsoil': 30,
        'Sand Content Topsoil': 50, 'Organic Carbon Topsoil %': 2,
        'Topsoil Thickness m': .15, 'Saturated Hydraulic Topsoil mm/hr': 8,
        'Clay Content Subsoil %': 25, 'Silt Content Subsoil': 35,
        'Sand Content Subsoil': 40, 'Organic Carbon Subsoil %': 1,
        'Saturated Hydraulic Subsoil mm/hr': 4,
    }
    monkeypatch.setattr(module, 'query_asris', lambda *_: {
        key: {'Value': value} for key, value in values.items()})
    monkeypatch.setattr(module, 'ASRISgrid', lambda: SimpleNamespace(query=lambda *_: {'asc': 'Test'}))
    monkeypatch.setattr(module, 'Lu10v5ua', lambda: SimpleNamespace(query_dom=lambda **_: 'forest'))
    module.build_asris_soils([('101', (0, 0))], str(tmp_path))
    artifacts = list(tmp_path.glob('*.sol'))
    assert len(artifacts) == 3
    # Native validity of the base legacy header is outside this boundary check.
    for artifact in artifacts:
        rows = horizon_records(artifact.read_text())
        assert [float(row[0]) for row in rows] == [150, 200, 300]
        assert rows[1][1:] == rows[2][1:]


@pytest.mark.parametrize('version', [7778, 2006.2])
@pytest.mark.parametrize('count', [0, 2])
def test_channel_soil_writers_emit_normalized_profiles(tmp_path, version, count):
    from wepppy.nodb.core.wepp import Wepp
    import logging

    context = SimpleNamespace(
        runs_dir=str(tmp_path), logger=logging.getLogger(__name__),
        watershed_instance=SimpleNamespace(chn_n=count),
        soils_instance=SimpleNamespace(chn_iter=lambda: [
            (str(i), SimpleNamespace(as_dict=lambda: {'avke': 7}))
            for i in range(count)]))
    if version == 7778:
        Wepp._prep_7778_channel_soils(context, .0001, 2)
    else:
        translator = SimpleNamespace(chn_enum=lambda top: top)
        Wepp._prep_2006_channel_soils(context, translator, .0001, 2, 5)
    artifact = tmp_path / 'pw0.sol'
    text = artifact.read_text()
    assert ensure_200mm_boundary(text) == text
    if not count:
        assert text.splitlines()[-1] == '0 1'
        return
    soil = WeppSoilUtil(str(artifact))
    assert len(soil.obj['ofes']) == count
    for ofe in soil.obj['ofes']:
        assert ofe['nsl'] == 2
        assert [h['solthk'] for h in ofe['horizons']] == [200, 400]
        assert {k: v for k, v in ofe['horizons'][0].items() if k != 'solthk'} == {
            k: v for k, v in ofe['horizons'][1].items() if k != 'solthk'}
