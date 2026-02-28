from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from wepppy.rq.weppcloudr_rq import (
    WeppcloudRError,
    _assert_no_retired_root_resources,
    _build_render_deval_expression,
    render_deval_details_rq,
)

pytestmark = pytest.mark.unit


def test_render_deval_details_rq_accepts_legacy_parquet_overrides_kwarg() -> None:
    signature = inspect.signature(render_deval_details_rq)
    assert "parquet_overrides" in signature.parameters


def test_assert_no_retired_root_resources_allows_clean_directory(tmp_path: Path) -> None:
    (tmp_path / "landuse").mkdir()
    _assert_no_retired_root_resources(tmp_path)


def test_assert_no_retired_root_resources_rejects_retired_sidecars(tmp_path: Path) -> None:
    (tmp_path / "landuse.parquet").write_text("x", encoding="utf-8")
    (tmp_path / "climate.wepp_cli.parquet").write_text("x", encoding="utf-8")

    with pytest.raises(WeppcloudRError, match="Migration required"):
        _assert_no_retired_root_resources(tmp_path)


def test_assert_no_retired_root_resources_rejects_mixed_canonical_and_sidecar_state(
    tmp_path: Path,
) -> None:
    (tmp_path / "landuse").mkdir()
    (tmp_path / "landuse" / "landuse.parquet").write_text("canonical", encoding="utf-8")
    (tmp_path / "landuse.parquet").write_text("retired", encoding="utf-8")

    with pytest.raises(WeppcloudRError, match="Migration required"):
        _assert_no_retired_root_resources(tmp_path)


def test_build_render_deval_expression_uses_stable_render_signature() -> None:
    expression = _build_render_deval_expression("{}")

    assert "render_deval(payload$run_path, payload$runid, payload$config," in expression
    assert "skip_cache = payload$skip_cache" in expression
    assert "parquet_overrides" not in expression
    assert "do.call(" not in expression
