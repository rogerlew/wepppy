from __future__ import annotations

import pytest

from wepppy.nodb.mods.path_ce.data_loader import (
    PathCEDataError,
    _resolve_omni_dir,
)

pytestmark = pytest.mark.unit


def _touch_expected(base):
    (base / "scenarios.hillslope_summaries.parquet").touch()
    (base / "contrasts.out.parquet").touch()


def test_resolve_omni_uses_pups_layout(tmp_path):
    canonical = tmp_path / "omni"
    canonical.mkdir(parents=True)
    _touch_expected(canonical)

    resolved = _resolve_omni_dir(tmp_path)
    assert resolved == canonical


def test_resolve_omni_raises_when_missing(tmp_path):
    with pytest.raises(PathCEDataError):
        _resolve_omni_dir(tmp_path)
