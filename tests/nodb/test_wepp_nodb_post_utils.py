from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.wepp_nodb_post_utils as post_utils

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("watershed_pending", "expected_delete_after_interchange"),
    [(True, False), (False, True)],
)
def test_ensure_hillslope_interchange_defers_delete_until_post_watershed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    watershed_pending: bool,
    expected_delete_after_interchange: bool,
) -> None:
    calls: list[tuple[Path, bool]] = []
    wepp = SimpleNamespace(
        output_dir=str(tmp_path / "wepp" / "output"),
        wepp_interchange_dir=str(tmp_path / "wepp" / "output" / "interchange"),
        delete_after_interchange=True,
    )
    climate = SimpleNamespace(
        is_single_storm=False,
        calendar_start_year=2004,
        delete_after_interchange=False,
    )

    monkeypatch.setattr(
        post_utils,
        "run_wepp_hillslope_interchange",
        lambda path, **kwargs: calls.append((Path(path), kwargs["delete_after_interchange"])),
    )

    post_utils.ensure_hillslope_interchange(
        wepp,
        climate,
        watershed_pending=watershed_pending,
    )

    assert calls == [(Path(wepp.output_dir), expected_delete_after_interchange)]


def test_ensure_watershed_interchange_runs_deferred_hillslope_cleanup_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = SimpleNamespace(
        output_dir=str(tmp_path / "wepp" / "output"),
        wepp_interchange_dir=str(tmp_path / "wepp" / "output" / "interchange"),
        delete_after_interchange=True,
    )
    climate = SimpleNamespace(
        is_single_storm=False,
        calendar_start_year=1999,
        delete_after_interchange=False,
    )

    watershed_calls: list[tuple[Path, bool]] = []
    cleanup_calls: list[tuple[Path, bool, bool, bool]] = []
    doc_calls: list[str] = []

    monkeypatch.setattr(
        post_utils,
        "run_wepp_watershed_interchange",
        lambda path, **kwargs: watershed_calls.append((Path(path), kwargs["delete_after_interchange"])),
    )
    monkeypatch.setattr(
        post_utils,
        "cleanup_hillslope_sources_for_completed_interchange",
        lambda path, **kwargs: cleanup_calls.append(
            (
                Path(path),
                kwargs["run_loss_interchange"],
                kwargs["run_soil_interchange"],
                kwargs["run_wat_interchange"],
            )
        ),
    )
    monkeypatch.setattr(
        post_utils,
        "generate_interchange_documentation",
        lambda path: doc_calls.append(str(path)),
    )

    post_utils.ensure_watershed_interchange(wepp, climate)

    assert watershed_calls == [(Path(wepp.output_dir), True)]
    assert cleanup_calls == [(Path(wepp.output_dir), True, True, True)]
    assert doc_calls == [wepp.wepp_interchange_dir]


def test_ensure_watershed_interchange_skips_rebuild_but_still_runs_deferred_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "wepp" / "output"
    interchange_dir = output_dir / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    (interchange_dir / "pass_pw0.events.parquet").write_text("ready", encoding="utf-8")

    wepp = SimpleNamespace(
        output_dir=str(output_dir),
        wepp_interchange_dir=str(interchange_dir),
        delete_after_interchange=True,
    )
    climate = SimpleNamespace(
        is_single_storm=True,
        calendar_start_year=2010,
        delete_after_interchange=False,
    )

    cleanup_calls: list[tuple[Path, bool, bool, bool]] = []
    monkeypatch.setattr(
        post_utils,
        "run_wepp_watershed_interchange",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected rebuild")),
    )
    monkeypatch.setattr(
        post_utils,
        "cleanup_hillslope_sources_for_completed_interchange",
        lambda path, **kwargs: cleanup_calls.append(
            (
                Path(path),
                kwargs["run_loss_interchange"],
                kwargs["run_soil_interchange"],
                kwargs["run_wat_interchange"],
            )
        ),
    )
    monkeypatch.setattr(
        post_utils,
        "generate_interchange_documentation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected docs refresh")),
    )

    post_utils.ensure_watershed_interchange(wepp, climate)

    assert cleanup_calls == [(output_dir, False, False, False)]
