from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.runtime_paths.errors import NoDirError
from wepppy.wepp.interchange._utils import _ensure_cli_parquet

pytestmark = pytest.mark.unit


def test_ensure_cli_parquet_prefers_canonical_directory_file(tmp_path: Path) -> None:
    cli_dir = tmp_path / "climate"
    cli_dir.mkdir(parents=True)
    canonical = cli_dir / "wepp_cli.parquet"
    canonical.write_text("ok", encoding="utf-8")

    resolved = _ensure_cli_parquet(cli_dir)

    assert resolved == canonical


def test_ensure_cli_parquet_rejects_retired_root_sidecar(tmp_path: Path) -> None:
    cli_dir = tmp_path / "climate"
    cli_dir.mkdir(parents=True)
    retired = tmp_path / "climate.wepp_cli.parquet"
    retired.write_text("retired", encoding="utf-8")

    with pytest.raises(NoDirError, match="NODIR_MIGRATION_REQUIRED"):
        _ensure_cli_parquet(cli_dir)
