from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.topo.wbt.wbt_topaz_emulator import WhiteboxToolsTopazEmulator


pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
TOPAZ_FIXTURE = (
    REPO_ROOT.parent
    / "weppcloud-wbt"
    / "test_fixtures"
    / "topaz_condition_dem"
    / "dem.tif"
)


def test_installed_topaz_conditioning_creates_relief(tmp_path: Path) -> None:
    if not TOPAZ_FIXTURE.exists():
        pytest.skip(f"Missing weppcloud-wbt fixture: {TOPAZ_FIXTURE}")

    emulator = WhiteboxToolsTopazEmulator(
        wbt_wd=str(tmp_path),
        dem_fn=str(TOPAZ_FIXTURE),
        verbose=False,
        raise_on_error=True,
    )

    emulator._create_relief(fill_or_breach="topaz")

    relief = Path(emulator.relief)
    assert relief.is_file()
    assert relief.stat().st_size > 0
