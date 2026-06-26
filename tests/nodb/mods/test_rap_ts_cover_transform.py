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
