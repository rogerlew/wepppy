from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.nodb.mods.disturbed.disturbed import Disturbed


@pytest.mark.unit
def test_extended_lookup_temp_file_is_run_scoped_and_writable(tmp_path: Path) -> None:
    disturbed = object.__new__(Disturbed)
    disturbed.wd = str(tmp_path)

    tmp_lookup = Path(disturbed._new_extended_land_soil_lookup_tmp_path())

    assert tmp_lookup.parent == (tmp_path / "disturbed")
    assert tmp_lookup.name.startswith("extended_disturbed_land_soil_lookup.")
    assert tmp_lookup.suffix == ".csv"
    assert "wepppy/nodb/mods/disturbed/data" not in str(tmp_lookup)
    assert tmp_lookup.exists()

    tmp_lookup.write_text("ok\n")
    tmp_lookup.unlink()
