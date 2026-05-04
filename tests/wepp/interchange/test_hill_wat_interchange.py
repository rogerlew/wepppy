from pathlib import Path

import pyarrow.parquet as pq
import pytest

from .module_loader import cleanup_import_state, load_module

load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")
load_module("wepppy.wepp.interchange.schema_utils", "wepppy/wepp/interchange/schema_utils.py")
load_module("wepppy.wepp.interchange._utils", "wepppy/wepp/interchange/_utils.py")
concurrency_module = load_module("wepppy.wepp.interchange.concurrency", "wepppy/wepp/interchange/concurrency.py")
wat_module = load_module("wepppy.wepp.interchange.hill_wat_interchange", "wepppy/wepp/interchange/hill_wat_interchange.py")
cleanup_import_state()

pytestmark = pytest.mark.unit


_HEADER_BASE = """ ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  OFE    J    Y      P      RM     Q                Ep      Es      Er     Dp       UpStrmQ   SubRIn    latqcc Total-Soil frozwt Snow-Water QOFE            Tile    Irr        Area
  #      -    -      mm     mm     mm               mm      mm      mm       mm      mm           mm      mm   Water(mm)   mm        mm      mm             mm      mm         m^2
 ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

"""

_HEADER_ENRICHED = """ ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  OFE    J    Y      P      RM     Q                Ep      Es      Er     Dp       UpStrmQ   SubRIn    latqcc Total-Soil frozwt Snow-Water QOFE            Tile    Irr        Area SoilWaterTotal ProfileDepth ProfilePorosityCap ProfileFCStore ProfileWPStore InterceptionStorage
  #      -    -      mm     mm     mm               mm      mm      mm       mm      mm           mm      mm   Water(mm)   mm        mm      mm             mm      mm         m^2             mm           mm                 mm             mm             mm                  mm
 ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

"""

_HEADER_ENRICHED_NO_INTERCEPTION = """ ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  OFE    J    Y      P      RM     Q                Ep      Es      Er     Dp       UpStrmQ   SubRIn    latqcc Total-Soil frozwt Snow-Water QOFE            Tile    Irr        Area SoilWaterTotal ProfileDepth ProfilePorosityCap ProfileFCStore ProfileWPStore
  #      -    -      mm     mm     mm               mm      mm      mm       mm      mm           mm      mm   Water(mm)   mm        mm      mm             mm      mm         m^2             mm           mm                 mm             mm             mm
 ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

"""


def _write_wat(path: Path, header: str, row: str) -> None:
    path.write_text(header + row + "\n", encoding="utf-8")


def test_hill_wat_interchange_legacy_layout_emits_null_optional_terms(tmp_path: Path) -> None:
    workdir = tmp_path / "output"
    workdir.mkdir()
    _write_wat(
        workdir / "H1.wat.dat",
        _HEADER_BASE,
        "     1    1 2000   10.00   10.00   0.0000000E+00    0.10    0.20    0.30    0.40   0.0000000E+00    0.00    0.50  100.00    1.25    0.00    0.0000000E+00    0.00    0.00      50.00",
    )

    target = wat_module.run_wepp_hillslope_wat_interchange(workdir)
    df = pq.read_table(target).to_pandas()

    assert df.loc[0, "Total-Soil Water"] == pytest.approx(100.0)
    assert df.loc[0, "frozwt"] == pytest.approx(1.25)
    for column in wat_module.WAT_OPTIONAL_COLUMN_NAMES:
        assert column in df.columns
        assert df[column].isna().all()


def test_hill_wat_interchange_parses_enriched_storage_terms(tmp_path: Path) -> None:
    workdir = tmp_path / "output"
    workdir.mkdir()
    _write_wat(
        workdir / "H1.wat.dat",
        _HEADER_ENRICHED,
        "     1    1 2000   10.00   10.00   0.0000000E+00    0.10    0.20    0.30    0.40   0.0000000E+00    0.00    0.50  100.00    1.25    0.00    0.0000000E+00    0.00    0.00      50.00         101.25      1000.00             510.00         310.00         130.00               0.45",
    )

    target = wat_module.run_wepp_hillslope_wat_interchange(workdir)
    df = pq.read_table(target).to_pandas()

    assert df.loc[0, "SoilWaterTotal"] == pytest.approx(101.25)
    assert df.loc[0, "ProfileDepth"] == pytest.approx(1000.0)
    assert df.loc[0, "ProfilePorosityCap"] == pytest.approx(510.0)
    assert df.loc[0, "ProfileFCStore"] == pytest.approx(310.0)
    assert df.loc[0, "ProfileWPStore"] == pytest.approx(130.0)
    assert df.loc[0, "InterceptionStorage"] == pytest.approx(0.45)


def test_hill_wat_interchange_parses_enriched_layout_without_interception(tmp_path: Path) -> None:
    workdir = tmp_path / "output"
    workdir.mkdir()
    _write_wat(
        workdir / "H1.wat.dat",
        _HEADER_ENRICHED_NO_INTERCEPTION,
        "     1    1 2000   10.00   10.00   0.0000000E+00    0.10    0.20    0.30    0.40   0.0000000E+00    0.00    0.50  100.00    1.25    0.00    0.0000000E+00    0.00    0.00      50.00         101.25      1000.00             510.00         310.00         130.00",
    )

    target = wat_module.run_wepp_hillslope_wat_interchange(workdir)
    df = pq.read_table(target).to_pandas()

    assert df.loc[0, "SoilWaterTotal"] == pytest.approx(101.25)
    assert df.loc[0, "ProfileDepth"] == pytest.approx(1000.0)
    assert df.loc[0, "ProfilePorosityCap"] == pytest.approx(510.0)
    assert df.loc[0, "ProfileFCStore"] == pytest.approx(310.0)
    assert df.loc[0, "ProfileWPStore"] == pytest.approx(130.0)
    assert df["InterceptionStorage"].isna().all()


def test_hill_wat_interchange_rejects_unknown_extra_columns(tmp_path: Path) -> None:
    source = tmp_path / "H1.wat.dat"
    _write_wat(
        source,
        _HEADER_ENRICHED.replace("ProfileWPStore", "UnexpectedExtra"),
        "     1    1 2000   10.00   10.00   0.0000000E+00    0.10    0.20    0.30    0.40   0.0000000E+00    0.00    0.50  100.00    1.25    0.00    0.0000000E+00    0.00    0.00      50.00         101.25      1000.00             510.00         310.00         130.00               0.45",
    )

    with pytest.raises(ValueError, match="Unexpected WAT column layout"):
        wat_module._parse_wat_file(source)


def test_hill_wat_interchange_normalizes_missing_rust_optional_columns() -> None:
    columns = {"wepp_id": [1, 2], "P": [1.0, 2.0]}

    normalized = wat_module._normalize_rust_optional_columns(columns)
    for column in wat_module.WAT_OPTIONAL_COLUMN_NAMES:
        assert normalized[column] == [None, None]
    assert normalized["wepp_id"] == [1, 2]
    assert normalized["P"] == [1.0, 2.0]

    already_extended = {"wepp_id": [9], "SoilWaterTotal": [0.7], "ProfileDepth": [1000.0]}
    for column in wat_module.WAT_OPTIONAL_COLUMN_NAMES:
        already_extended.setdefault(column, [None])
    assert wat_module._normalize_rust_optional_columns(already_extended) is already_extended
