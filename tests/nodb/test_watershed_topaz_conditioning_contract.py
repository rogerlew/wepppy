from __future__ import annotations

import configparser
from pathlib import Path

import jsonpickle
import pytest

from wepppy.nodb.core.watershed import (
    WBT_FILL_OR_BREACH_VALUES,
    Watershed,
)

pytestmark = pytest.mark.unit


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "wepppy" / "nodb" / "configs"


def _read_config(name: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(CONFIG_DIR / name)
    return parser


def _call_conditioning_setter(watershed: Watershed, value: str) -> None:
    setter = Watershed.wbt_fill_or_breach.fset
    assert setter is not None
    setter.__wrapped__(watershed, value)


def test_disturbed9002_wbt_is_the_only_representative_topaz_default() -> None:
    disturbed = _read_config("disturbed9002_wbt.cfg")
    sibling = _read_config("disturbed9002-10m-wbt.cfg")
    general = _read_config("0-wbt.cfg")

    assert disturbed.get("watershed.wbt", "fill_or_breach") == '"topaz"'
    assert sibling.get("watershed.wbt", "fill_or_breach") == '"breach_least_cost"'
    assert general.get("watershed.wbt", "fill_or_breach") == '"breach_least_cost"'


@pytest.mark.parametrize("value", sorted(WBT_FILL_OR_BREACH_VALUES))
def test_watershed_conditioning_setter_accepts_all_canonical_values(
    value: str,
) -> None:
    watershed = object.__new__(Watershed)

    _call_conditioning_setter(watershed, value)

    assert watershed.wbt_fill_or_breach == value


def test_watershed_conditioning_setter_rejects_invalid_value_without_assert() -> None:
    watershed = object.__new__(Watershed)

    with pytest.raises(ValueError, match="Invalid wbt_fill_or_breach"):
        _call_conditioning_setter(watershed, "../../hostile")


@pytest.mark.parametrize("legacy_value", ("fill", "breach", "breach_least_cost"))
def test_persisted_legacy_conditioning_survives_new_config_default(
    tmp_path: Path,
    legacy_value: str,
) -> None:
    watershed = object.__new__(Watershed)
    watershed._wbt_fill_or_breach = legacy_value
    persisted = tmp_path / "watershed.nodb"
    persisted.write_text(jsonpickle.encode(watershed), encoding="utf-8")

    restored = jsonpickle.decode(persisted.read_text(encoding="utf-8"))

    assert restored.wbt_fill_or_breach == legacy_value
