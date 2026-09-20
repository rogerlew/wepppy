"""New thinning assets resolve through catalogs and the real WEPP input writer."""
from pathlib import Path
from types import SimpleNamespace
import logging

import pytest

from wepppy.wepp.management import get_management_summary, load_map, read_management

pytestmark = pytest.mark.integration
DATA = Path(__file__).resolve().parents[3] / 'wepppy/wepp/management/data'


def _parameters(data):
    return {key: value if isinstance(value, (int, float, str, bool)) else str(value)
            for key, value in vars(data).items() if key != 'root'}


@pytest.mark.parametrize('catalog', ['disturbed', 'c3s-disturbed', 'au-disturbed',
                                     'eu-corine-disturbed', 'revegetation'])
@pytest.mark.parametrize('canopy', [30, 50])
@pytest.mark.parametrize('ground', [75, 85, 90, 93])
def test_thinning_catalog_roundtrip(tmp_path, catalog, canopy, ground):
    mapping = load_map(str(DATA / f'{catalog}.json'))
    matches = [key for key, row in mapping.items()
               if row.get('DisturbedClass') == f'thinning_{canopy}_{ground}']
    assert len(matches) == 1
    summary = get_management_summary(matches[0], str(DATA / f'{catalog}.json'))
    source = read_management(str(DATA / f'UnDisturbed/Thinning_40_{ground}.man'))
    man = summary.get_management()
    assert (summary.cancov, summary.inrcov, summary.rilcov) == pytest.approx(
        (canopy / 100, ground / 100, ground / 100))
    assert _parameters(man.plants[0].data) == _parameters(source.plants[0].data)
    expected_ini = dict(_parameters(source.inis[0].data), cancov=canopy / 100)
    assert _parameters(man.inis[0].data) == expected_ini
    rendered = tmp_path / 'roundtrip.man'
    rendered.write_text(str(man))
    restored = read_management(str(rendered))
    assert _parameters(restored.inis[0].data) == expected_ini


@pytest.mark.parametrize('canopy', [30, 50])
@pytest.mark.parametrize('ground', [75, 85, 90, 93])
def test_thinning_single_ofe_prepared_input(tmp_path, monkeypatch, canopy, ground):
    from wepppy.nodb.core.wepp_prep_service import WeppPrepService
    from wepppy.nodb.mods.disturbed import Disturbed
    from wepppy.nodb.mods import RAP_TS

    mapping = load_map('disturbed')
    key = next(k for k, row in mapping.items()
               if row.get('DisturbedClass') == f'thinning_{canopy}_{ground}')
    summary = get_management_summary(key, 'disturbed')
    monkeypatch.setattr(Disturbed, 'tryGetInstance', lambda wd: None)
    monkeypatch.setattr(RAP_TS, 'tryGetInstance', lambda wd: None)
    runs = tmp_path / 'wepp/runs'
    runs.mkdir(parents=True)
    wepp = SimpleNamespace(wd=str(tmp_path), runs_dir=str(runs), mods=[],
        logger=logging.getLogger(__name__),
        landuse_instance=SimpleNamespace(hillslope_cancovs=None,
            domlc_d={'101': key}, managements={key: summary}),
        climate_instance=SimpleNamespace(input_years=2, year0=2000),
        soils_instance=SimpleNamespace(bd_d={'soil': 1.1}, domsoil_d={'101': 'soil'}))
    WeppPrepService().prep_managements(wepp, SimpleNamespace(wepp=lambda **kw: 1))
    prepared = read_management(str(runs / 'p1.man'))
    assert (prepared.inis[0].data.cancov, prepared.inis[0].data.inrcov,
            prepared.inis[0].data.rilcov) == pytest.approx(
                (canopy / 100, ground / 100, ground / 100))
    assert _parameters(prepared.plants[0].data) == _parameters(summary.get_management().plants[0].data)
