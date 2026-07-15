from pathlib import Path
import shutil

import pyarrow.parquet as pq
import pytest

from .module_loader import PROJECT_OUTPUT, cleanup_import_state, load_module
load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")
load_module("wepppy.wepp.interchange.schema_utils", "wepppy/wepp/interchange/schema_utils.py")
load_module("wepppy.wepp.interchange._utils", "wepppy/wepp/interchange/_utils.py")
concurrency_module = load_module("wepppy.wepp.interchange.concurrency", "wepppy/wepp/interchange/concurrency.py")
wat_module = load_module("wepppy.wepp.interchange.hill_wat_interchange", "wepppy/wepp/interchange/hill_wat_interchange.py")
cleanup_import_state()


def _write_multi_ofe_wat(path: Path) -> None:
    path.write_text(
        """ ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  OFE    J    Y      P      RM     Q                Ep      Es      Er     Dp       UpStrmQ   SubRIn    latqcc Total-Soil frozwt Snow-Water QOFE            Tile    Irr        Area
  #      -    -      mm     mm     mm               mm      mm      mm       mm      mm           mm      mm   Water(mm)   mm        mm      mm             mm      mm         m^2
 ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

     1    1 2000   10.00   10.00   0.0000000E+00    0.10    0.20    0.30    0.40   0.0000000E+00    0.00    0.50  100.00    0.00    0.00    0.0000000E+00    0.00    0.00      50.00
     2    1 2000   10.00   10.00   0.0000000E+00    0.10    0.20    0.30    0.40   0.0000000E+00    0.00    0.50  100.00    0.00    0.00    0.0000000E+00    0.00    0.00      75.00
     1    2 2000   11.00   11.00   0.0000000E+00    0.10    0.20    0.30    0.40   0.0000000E+00    0.00    0.50  100.00    0.00    0.00    0.0000000E+00    0.00    0.00      50.00
     2    2 2000   11.00   11.00   0.0000000E+00    0.10    0.20    0.30    0.40   0.0000000E+00    0.00    0.50  100.00    0.00    0.00    0.0000000E+00    0.00    0.00      75.00
""",
        encoding="utf-8",
    )


def test_wat_interchange_writes_parquet(tmp_path, monkeypatch):
    src = PROJECT_OUTPUT
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    calls = []

    def _wrapper(files, parser, schema, target_path, **kwargs):
        file_list = [Path(p) for p in files]
        calls.append({"files": file_list, "schema": schema, "kwargs": dict(kwargs)})
        kwargs["max_workers"] = 0
        return concurrency_module.write_parquet_with_pool(file_list, parser, schema, target_path, **kwargs)

    monkeypatch.setattr(wat_module, "write_parquet_with_pool", _wrapper)
    monkeypatch.setattr(
        wat_module,
        "load_rust_interchange",
        lambda: (None, RuntimeError("disabled for pool-path regression")),
    )

    target = wat_module.run_wepp_hillslope_wat_interchange(workdir, max_workers=2)
    assert target.exists()
    assert calls
    assert all(p.name.lower().endswith(".wat.dat") for p in calls[0]["files"])
    assert calls[0]["kwargs"]["max_workers"] == 2

    table = pq.read_table(target)
    assert table.schema == wat_module.SCHEMA
    assert table.num_rows > 0

    df = table.to_pandas()
    assert set(df["wepp_id"].unique()) == {1, 2, 3}
    assert (df["ofe_id"] == df["OFE"]).all()

    first_row = df.iloc[0]
    assert first_row["month"] == 1
    assert first_row["day_of_month"] == 1
    assert pytest.approx(first_row["P"], rel=1e-6) == 12.20


def test_wat_interchange_prefers_direct_rust_writer(tmp_path, monkeypatch):
    workdir = tmp_path / "output"
    workdir.mkdir()
    first = workdir / "H1.wat.dat"
    second = workdir / "H2.wat.dat"
    _write_multi_ofe_wat(first)
    _write_multi_ofe_wat(second)
    calls = []

    class FakeRust:
        @staticmethod
        def hillslope_wat_files_to_parquet(
            files,
            target,
            major,
            minor,
            *,
            cli_calendar_path,
            compression,
        ):
            calls.append(
                {
                    "files": files,
                    "target": target,
                    "version": (major, minor),
                    "calendar": cli_calendar_path,
                    "compression": compression,
                }
            )
            pq.write_table(wat_module.EMPTY_TABLE, target)

    monkeypatch.setattr(wat_module, "load_rust_interchange", lambda: (FakeRust(), None))
    monkeypatch.setattr(wat_module, "resolve_cli_calendar_path", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        wat_module,
        "write_parquet_with_pool",
        lambda *args, **kwargs: pytest.fail("pool path should not run"),
    )

    target = wat_module.run_wepp_hillslope_wat_interchange(workdir, max_workers=16)

    assert target.is_file()
    assert calls == [
        {
            "files": [str(first), str(second)],
            "target": str(target),
            "version": wat_module.version_args(),
            "calendar": None,
            "compression": "snappy",
        }
    ]


def test_direct_rust_wat_writer_matches_python_schema_and_values(tmp_path):
    rust_mod, rust_err = wat_module.load_rust_interchange()
    if rust_mod is None or not hasattr(rust_mod, "hillslope_wat_files_to_parquet"):
        pytest.skip(f"direct Rust WAT writer unavailable: {rust_err}")
    first = tmp_path / "H1.wat.dat"
    second = tmp_path / "H2.wat.dat"
    target = tmp_path / "H.wat.parquet"
    _write_multi_ofe_wat(first)
    _write_multi_ofe_wat(second)
    major, minor = wat_module.version_args()

    rust_mod.hillslope_wat_files_to_parquet(
        [str(first), str(second)],
        str(target),
        major,
        minor,
        cli_calendar_path=None,
        compression="snappy",
    )

    observed = pq.read_table(target)
    expected = wat_module.pa.concat_tables(
        [wat_module._parse_wat_file(first), wat_module._parse_wat_file(second)]
    )
    assert observed.schema == wat_module.SCHEMA
    assert observed.equals(expected)


def test_wat_interchange_handles_missing_files(tmp_path):
    workdir = tmp_path / "empty_output"
    workdir.mkdir()

    target = wat_module.run_wepp_hillslope_wat_interchange(workdir)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == wat_module.SCHEMA
    assert table.num_rows == 0


def test_wat_interchange_uses_calendar_sim_day_for_multi_ofe(tmp_path):
    workdir = tmp_path / "output"
    workdir.mkdir()
    _write_multi_ofe_wat(workdir / "H1.wat.dat")

    target = wat_module.run_wepp_hillslope_wat_interchange(workdir)
    df = pq.read_table(target).to_pandas()
    df = df.sort_values(["year", "julian", "ofe_id"]).reset_index(drop=True)

    assert df["sim_day_index"].tolist() == [1, 1, 2, 2]
    assert df.groupby(["year", "julian"])["sim_day_index"].nunique().eq(1).all()
