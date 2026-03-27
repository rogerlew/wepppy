from __future__ import annotations

import configparser
from pathlib import Path

import numpy as np
import pytest
from wepppy.all_your_base import isfloat
from wepppy.nodb.core.soils import Soils
from wepppy.wepp.soils.utils import WeppSoilUtil

rasterio = pytest.importorskip("rasterio", reason="rasterio required for Tenerife soil catalog tests")

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SOILS_DIR = _REPO_ROOT / "wepppy/locales/tenerife/soils"
_LEGACY_CONFIG = _REPO_ROOT / "wepppy/nodb/configs/legacy/tenerife-disturbed.toml"
_SUPPORTED_MAPS = ("tf_soil_5.tif", "tf_soil_25.tif")


def _unique_raster_values(raster_path: Path) -> set[int]:
    values: set[int] = set()
    with rasterio.open(raster_path) as dataset:
        for _, window in dataset.block_windows(1):
            block = dataset.read(1, window=window)
            values.update(int(value) for value in np.unique(block))
    return values


def test_supported_tenerife_soil_rasters_have_runtime_sol_files() -> None:
    soils_db_dir = _SOILS_DIR / "db"

    for raster_name in _SUPPORTED_MAPS:
        values = _unique_raster_values(_SOILS_DIR / raster_name)
        runtime_codes = {value for value in values if value != 255}
        missing = sorted(code for code in runtime_codes if not (soils_db_dir / f"{code}.sol").exists())
        assert missing == [], f"{raster_name} is missing runtime soil files for codes {missing}"

        assert 20 in runtime_codes
        assert 21 in runtime_codes


def _read_cfg(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(path)
    return parser


def _cfg_value(parser: configparser.ConfigParser, section: str, key: str) -> str:
    return parser.get(section, key).strip().strip('"')


def test_active_tenerife_configs_reference_supported_dem_and_soil_assets() -> None:
    twenty_five = _read_cfg(_REPO_ROOT / "wepppy/nodb/configs/tenerife-disturbed.cfg")
    five = _read_cfg(_REPO_ROOT / "wepppy/nodb/configs/tenerife-5m-disturbed.cfg")

    assert _cfg_value(twenty_five, "general", "dem_db") == "tenerife/136_MDT25_TF"
    assert _cfg_value(five, "general", "dem_db") == "tenerife/MDT05_Tenerife"
    assert _cfg_value(twenty_five, "soils", "soils_map") == "LOCALES_DIR/tenerife/soils/tf_soil_25.tif"
    assert _cfg_value(five, "soils", "soils_map") == "LOCALES_DIR/tenerife/soils/tf_soil_5.tif"


def test_retired_tenerife_legacy_soil_assets_are_absent() -> None:
    assert (_SOILS_DIR / "tf_soil_10.tif").exists()
    assert not any((_SOILS_DIR / "db").glob("*.template.sol"))
    assert not (_SOILS_DIR / "db/process.py").exists()
    assert not _LEGACY_CONFIG.exists()


@pytest.mark.unit
def test_soils_map_property_expands_locales_dir_for_persisted_state() -> None:
    soils = Soils.__new__(Soils)
    soils._soils_map = "LOCALES_DIR/tenerife/soils/tf_soil_25.tif"
    soils._ssurgo_db = "None"

    assert soils.soils_map == str(_SOILS_DIR / "tf_soil_25.tif")


def _has_symbolic_wepp_parameters(soil: WeppSoilUtil) -> bool:
    for ofe in soil.obj.get("ofes", []):
        if not isfloat(ofe.get("ki")) or not isfloat(ofe.get("kr")) or not isfloat(ofe.get("shcrit")):
            return True
        for horizon in ofe.get("horizons", []):
            if not isfloat(horizon.get("ksat")):
                return True
    return False


def test_tenerife_soil_catalog_symbolic_materialization_audit() -> None:
    soils_db_dir = _SOILS_DIR / "db"
    symbolic_profiles = 0
    failures: list[tuple[str, str]] = []

    for soil_path in sorted(soils_db_dir.glob("*.sol")):
        soil = WeppSoilUtil(str(soil_path))
        if not _has_symbolic_wepp_parameters(soil):
            continue

        symbolic_profiles += 1
        try:
            materialized = WeppSoilUtil(
                str(soil_path),
                compute_erodibilities=True,
                compute_conductivity=True,
            ).to7778()
        except Exception as exc:
            failures.append((soil_path.name, str(exc)))
            continue

        for ofe_idx, ofe in enumerate(materialized.obj.get("ofes", [])):
            if not isfloat(ofe.get("ki")) or not isfloat(ofe.get("kr")) or not isfloat(ofe.get("shcrit")):
                failures.append((soil_path.name, f"ofe={ofe_idx} has non-numeric erodibility fields"))
            for hz_idx, horizon in enumerate(ofe.get("horizons", [])):
                if not isfloat(horizon.get("ksat")):
                    failures.append((soil_path.name, f"ofe={ofe_idx},horizon={hz_idx} has non-numeric ksat"))

    assert symbolic_profiles > 0
    assert failures == []
