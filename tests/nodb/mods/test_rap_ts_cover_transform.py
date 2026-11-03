from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.core import Landuse, Watershed
from wepppy.nodb.core.wepp import Wepp
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.rap.rap import RAP_Band
from wepppy.nodb.mods.rap.rap_ts import RAP_TS, _parse_fire_year
from wepppy.nodb.mods.revegetation import Revegetation

pytestmark = pytest.mark.unit


def test_parse_fire_year_supports_common_disturbed_formats() -> None:
    assert _parse_fire_year('06 01 24') == 2024
    assert _parse_fire_year('06/01/2024') == 2024
    assert _parse_fire_year('2024-06-01') == 2024


def test_get_cover_returns_wepp_fraction_from_percent_scale_rap_bands() -> None:
    year = '2020'
    topaz_id = '101'

    rap_ts = object.__new__(RAP_TS)
    rap_ts.data = {
        RAP_Band.TREE: {year: {topaz_id: 30.0}},
        RAP_Band.SHRUB: {year: {topaz_id: 20.0}},
        RAP_Band.PERENNIAL_FORB_AND_GRASS: {year: {topaz_id: 12.0}},
        RAP_Band.ANNUAL_FORB_AND_GRASS: {year: {topaz_id: 20.0}},
        RAP_Band.LITTER: {year: {topaz_id: 8.0}},
        RAP_Band.BARE_GROUND: {year: {topaz_id: 10.0}},
    }

    assert rap_ts.get_cover(topaz_id, year) == pytest.approx(0.82)


def test_prep_transformed_cover_handles_two_digit_fire_year(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    years = ['2020', '2021', '2022', '2023', '2024', '2025']
    topaz_id = '101'
    base_band = {year: {topaz_id: float((idx + 4) * 5)} for idx, year in enumerate(years)}

    rap_ts = object.__new__(RAP_TS)
    rap_ts.wd = str(tmp_path)
    rap_ts.logger = logging.getLogger('tests.rap_ts.cover_transform')
    rap_ts.data = {
        RAP_Band.TREE: base_band,
        RAP_Band.SHRUB: base_band,
        RAP_Band.PERENNIAL_FORB_AND_GRASS: base_band,
        RAP_Band.ANNUAL_FORB_AND_GRASS: base_band,
        RAP_Band.LITTER: base_band,
        RAP_Band.BARE_GROUND: base_band,
    }

    monkeypatch.setattr(
        Disturbed,
        'getInstance',
        classmethod(lambda cls, wd: SimpleNamespace(fire_date='06 01 24')),
    )
    monkeypatch.setattr(
        Wepp,
        'getInstance',
        classmethod(lambda cls, wd: SimpleNamespace(_multi_ofe=False)),
    )
    monkeypatch.setattr(
        Revegetation,
        'getInstance',
        classmethod(
            lambda cls, wd: SimpleNamespace(
                cover_transform={('forest low sev fire', 'Tree'): [0.25, 0.5] + [1.0] * 99}
            )
        ),
    )
    monkeypatch.setattr(
        Landuse,
        'getInstance',
        classmethod(
            lambda cls, wd: SimpleNamespace(
                managements={},
                identify_burn_class=lambda topaz_id: 'forest low sev fire',
            )
        ),
    )

    class _Translator:
        @staticmethod
        def iter_wepp_sub_ids() -> list[int]:
            return [1]

        @staticmethod
        def top(wepp: int) -> int:
            return 101

    monkeypatch.setattr(
        Watershed,
        'getInstance',
        classmethod(lambda cls, wd: SimpleNamespace(translator_factory=lambda: _Translator())),
    )

    rap_ts._prep_transformed_cover(str(tmp_path))

    output = (tmp_path / 'p1.cov').read_text(encoding='utf-8').splitlines()
    assert output[0].split() == years

    tree_values = [float(value) for value in output[1].split()]
    assert tree_values == [20.0, 25.0, 30.0, 35.0, 10.0, 20.0]


@pytest.mark.parametrize('transformed', [False, True])
def test_twelve_ofe_cover_blocks_follow_numeric_identity(tmp_path, monkeypatch, transformed):
    rap = object.__new__(RAP_TS)
    rap.wd = str(tmp_path)
    rap.logger = logging.getLogger('tests.rap.identity')
    bands = [RAP_Band.TREE, RAP_Band.SHRUB, RAP_Band.PERENNIAL_FORB_AND_GRASS,
             RAP_Band.ANNUAL_FORB_AND_GRASS, RAP_Band.LITTER, RAP_Band.BARE_GROUND]
    rap.data = {band: {'2024': {'101': {str(i): float(i + offset) for i in range(1, 13)}}}
                for offset, band in enumerate(bands)}
    monkeypatch.setattr(Wepp, 'getInstance', classmethod(lambda cls, wd: SimpleNamespace(_multi_ofe=True)))
    monkeypatch.setattr(Disturbed, 'getInstance', classmethod(lambda cls, wd: SimpleNamespace(fire_date='2024-01-01' if transformed else None)))
    reveg = SimpleNamespace(cover_transform={})
    monkeypatch.setattr(Revegetation, 'getInstance', classmethod(lambda cls, wd: reveg))
    monkeypatch.setattr(Revegetation, 'tryGetInstance', classmethod(lambda cls, wd: reveg))
    monkeypatch.setattr(Landuse, 'getInstance', classmethod(lambda cls, wd: SimpleNamespace(managements={}, identify_burn_class=lambda top, ofe: 'forest')))
    translator = SimpleNamespace(iter_wepp_sub_ids=lambda: [1], top=lambda wepp: 101)
    monkeypatch.setattr(Watershed, 'getInstance', classmethod(lambda cls, wd: SimpleNamespace(translator_factory=lambda: translator)))
    rap.prep_cover(str(tmp_path))
    rows = (tmp_path / 'p1.cov').read_text().splitlines()[1:]
    assert len(rows) == 12 * 6
    assert [float(rows[i * 6]) for i in range(12)] == list(range(1, 13))


@pytest.mark.parametrize('year_keys', [('2023', '2024'), (2023, 2024)])
@pytest.mark.parametrize('fallback', [True, False])
def test_single_ofe_missing_year_preserves_fallback(tmp_path, monkeypatch, year_keys, fallback):
    rap = object.__new__(RAP_TS)
    rap.wd = str(tmp_path)
    rap.logger = logging.getLogger('tests.rap.fallback')
    rap.data = {band: {year_keys[0]: {'101': 17.0}, year_keys[1]: {}}
                for band in (RAP_Band.TREE, RAP_Band.SHRUB,
                             RAP_Band.PERENNIAL_FORB_AND_GRASS,
                             RAP_Band.ANNUAL_FORB_AND_GRASS,
                             RAP_Band.LITTER, RAP_Band.BARE_GROUND)}
    monkeypatch.setattr(Wepp, 'getInstance', classmethod(lambda cls, wd: SimpleNamespace(_multi_ofe=False)))
    monkeypatch.setattr(Disturbed, 'getInstance', classmethod(lambda cls, wd: SimpleNamespace(fire_date=None)))
    monkeypatch.setattr(Revegetation, 'tryGetInstance', classmethod(lambda cls, wd: None))
    translator = SimpleNamespace(iter_wepp_sub_ids=lambda: [1], top=lambda wepp: 101)
    monkeypatch.setattr(Watershed, 'getInstance', classmethod(lambda cls, wd: SimpleNamespace(translator_factory=lambda: translator)))
    (tmp_path / 'simfire.txt').write_text('old transformed activation')
    rap.prep_cover(str(tmp_path), fallback=fallback)
    rows = (tmp_path / 'p1.cov').read_text().splitlines()
    assert rows[0].split() == ['2023', '2024']
    assert all(list(map(float, row.split())) == [17.0, 17.0 if fallback else 0.0] for row in rows[1:])
    assert not (tmp_path / 'simfire.txt').exists()
    assert next(tmp_path.glob('revegetation-input-*/simfire.txt')).read_text() == 'old transformed activation'


@pytest.mark.parametrize('saved,expected', [
    ('06 01 24', '6 1 2024\n'), ('2024-02-29', '2 29 2024\n'),
    ('06/01/2024', '6 1 2024\n'), (None, None),
])
def test_actual_firedate_writer_normalizes_and_clears(tmp_path, monkeypatch, saved, expected):
    import wepppy.nodb.core.wepp as wepp_module
    monkeypatch.setattr(wepp_module, 'require_feature_allowed', lambda *args: None)
    monkeypatch.setattr(Disturbed, 'getInstance', classmethod(lambda cls, wd: SimpleNamespace(fire_date=saved)))
    holder = SimpleNamespace(wd=str(tmp_path), runs_dir=str(tmp_path), logger=logging.getLogger('test.firedate'))
    (tmp_path / 'firedate.txt').write_text('prior date')
    Wepp._prep_firedate(holder)
    assert next(tmp_path.glob('revegetation-input-*/firedate.txt')).read_text() == 'prior date'
    if expected is None:
        assert not (tmp_path / 'firedate.txt').exists()
    else:
        assert (tmp_path / 'firedate.txt').read_text() == expected
    assert saved == getattr(Disturbed.getInstance(str(tmp_path)), 'fire_date')


def test_invalid_fire_date_preserves_prior_input(tmp_path, monkeypatch):
    import wepppy.nodb.core.wepp as wepp_module
    monkeypatch.setattr(wepp_module, 'require_feature_allowed', lambda *args: None)
    monkeypatch.setattr(Disturbed, 'getInstance', classmethod(lambda cls, wd: SimpleNamespace(fire_date='2023-02-29')))
    holder = SimpleNamespace(wd=str(tmp_path), runs_dir=str(tmp_path), logger=logging.getLogger('test.firedate'))
    (tmp_path / 'firedate.txt').write_text('prior date')
    with pytest.raises(ValueError):
        Wepp._prep_firedate(holder)
    assert (tmp_path / 'firedate.txt').read_text() == 'prior date'
