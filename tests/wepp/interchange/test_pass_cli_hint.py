from __future__ import annotations

import logging
from pathlib import Path

import pytest

from .module_loader import cleanup_import_state, load_module

pytestmark = pytest.mark.unit

pass_module = load_module(
    "wepppy.wepp.interchange.watershed_pass_interchange",
    "wepppy/wepp/interchange/watershed_pass_interchange.py",
)
rust_module = load_module(
    "wepppy.wepp.interchange._rust_interchange",
    "wepppy/wepp/interchange/_rust_interchange.py",
)
cleanup_import_state()


def _write_pass_header(path: Path) -> None:
    content = "\n".join(
        [
            " 1 --> VERSION NUMBER",
            " 1 NUMBER OF UNIQUE HILLSLOPES IN WATERSHED",
            " 10 WATERSHED MAXIMUM SIMULATION TIME (YEARS)",
            " 2000 BEGINNING YEAR OF WATERSHED CLIMATE FILE",
            "HILLSLOPE 1 p1.cli 1 2 3 10 0.1 0.2 0.3 0.4",
            "BEGIN HILLSLOPE HYDROLOGY AND SEDIMENT INFORMATION",
            "",
        ]
    )
    path.write_text(content)


def test_pass_cli_hint_forwarded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pass_path = tmp_path / "pass_pw0.txt"
    _write_pass_header(pass_path)

    hint = pass_module._extract_cli_hint(pass_path, False)
    assert hint == "p1.cli"

    climate_dir = tmp_path / "climate"
    climate_dir.mkdir()

    captured: dict[str, str | None] = {}

    def _fake_ensure(cli_dir: Path, cli_file_hint: str | None = None, log=None):
        captured["hint"] = cli_file_hint
        return None

    monkeypatch.setattr(rust_module, "_ensure_cli_parquet", _fake_ensure)

    rust_module.resolve_cli_calendar_path(tmp_path, cli_hint=hint, log=logging.getLogger("test"))
    assert captured["hint"] == "p1.cli"
