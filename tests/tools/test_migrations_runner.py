from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.query_engine import activate_query_engine
from wepppy.tools.migrations.interchange import migrate_interchange
from wepppy.tools.migrations.runner import refresh_query_catalog


def _write_parquet(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({"id": [1]}), path)


def test_refresh_query_catalog_forces_rebuild(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    first = run_dir / "wepp" / "output" / "interchange" / "a.parquet"
    second = run_dir / "wepp" / "output" / "interchange" / "b.parquet"

    _write_parquet(first)

    activate_query_engine(run_dir, run_interchange=False, force_refresh=True)
    catalog_path = run_dir / "_query_engine" / "catalog.json"
    original = json.loads(catalog_path.read_text())
    assert any(entry["path"] == "wepp/output/interchange/a.parquet" for entry in original["files"])

    _write_parquet(second)

    refresh_query_catalog(str(run_dir), dry_run=False)

    updated = json.loads(catalog_path.read_text())
    assert any(entry["path"] == "wepp/output/interchange/b.parquet" for entry in updated["files"])
    assert len(updated["files"]) >= 2


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


@pytest.mark.unit
def test_migrate_interchange_hbp_allows_missing_pass_pw0(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    _touch(run_dir / "wepp.nodb")
    _touch(run_dir / "climate.nodb")
    output_dir = run_dir / "wepp" / "output"
    _touch(output_dir / "chan.out")
    _touch(output_dir / "chanwb.out")
    _touch(output_dir / "chnwb.txt")
    _touch(output_dir / "ebe_pw0.txt")
    _touch(output_dir / "soil_pw0.txt")
    _touch(output_dir / "loss_pw0.txt")

    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "wepppy.nodb.core.Climate.getInstance",
        lambda _wd: SimpleNamespace(calendar_start_year=2001, is_single_storm=False),
    )
    monkeypatch.setattr(
        "wepppy.nodb.core.Wepp.getInstance",
        lambda _wd: SimpleNamespace(
            baseflow_opts=object(),
            delete_after_interchange=False,
            pass_family="hbp",
        ),
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.run_wepp_hillslope_interchange",
        lambda _path, **kwargs: calls.append(("hill", kwargs["pass_family"])),
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.run_wepp_watershed_interchange",
        lambda _path, **kwargs: calls.append(("watershed", kwargs["pass_family"])),
    )
    monkeypatch.setattr("wepppy.wepp.interchange.run_totalwatsed3", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "wepppy.wepp.interchange.generate_interchange_documentation",
        lambda *_args, **_kwargs: None,
    )

    applied, message = migrate_interchange(str(run_dir))

    assert applied is True
    assert "Generated interchange" in message
    assert ("hill", "hbp") in calls
    assert ("watershed", "hbp") in calls


@pytest.mark.unit
def test_migrate_interchange_reports_watershed_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    _touch(run_dir / "wepp.nodb")
    _touch(run_dir / "climate.nodb")
    output_dir = run_dir / "wepp" / "output"
    _touch(output_dir / "pass_pw0.txt")
    _touch(output_dir / "chan.out")
    _touch(output_dir / "chanwb.out")
    _touch(output_dir / "chnwb.txt")
    _touch(output_dir / "ebe_pw0.txt")
    _touch(output_dir / "soil_pw0.txt")
    _touch(output_dir / "loss_pw0.txt")

    monkeypatch.setattr(
        "wepppy.nodb.core.Climate.getInstance",
        lambda _wd: SimpleNamespace(calendar_start_year=2001, is_single_storm=False),
    )
    monkeypatch.setattr(
        "wepppy.nodb.core.Wepp.getInstance",
        lambda _wd: SimpleNamespace(
            baseflow_opts=object(),
            delete_after_interchange=False,
            pass_family="legacy_ascii",
        ),
    )
    monkeypatch.setattr("wepppy.wepp.interchange.run_wepp_hillslope_interchange", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "wepppy.wepp.interchange.run_wepp_watershed_interchange",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("watershed boom")),
    )

    applied, message = migrate_interchange(str(run_dir))

    assert applied is False
    assert "Watershed interchange failed" in message
    assert "watershed boom" in message


@pytest.mark.unit
def test_migrate_interchange_rejects_unsupported_pass_family(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    _touch(run_dir / "wepp.nodb")
    _touch(run_dir / "climate.nodb")
    output_dir = run_dir / "wepp" / "output"
    _touch(output_dir / "pass_pw0.txt")

    monkeypatch.setattr(
        "wepppy.nodb.core.Climate.getInstance",
        lambda _wd: SimpleNamespace(calendar_start_year=2001, is_single_storm=True),
    )
    monkeypatch.setattr(
        "wepppy.nodb.core.Wepp.getInstance",
        lambda _wd: SimpleNamespace(
            baseflow_opts=object(),
            delete_after_interchange=False,
            pass_family="auto",
        ),
    )

    applied, message = migrate_interchange(str(run_dir))

    assert applied is False
    assert "Failed to load run configuration" in message
    assert "pass_family must be 'legacy_ascii' or 'hbp'" in message
