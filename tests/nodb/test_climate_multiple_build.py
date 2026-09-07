from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from tests.nodb.lock_contention_utils import ensure_climate_stub
from wepppy.nodb.core.climate import Climate
from wepppy.nodb.core.climate_multiple_build import (
    ClimateMultipleBuildResult,
    ClimateMultipleBuildSupersededError,
    capture_multiple_build_inputs,
    finalize_multiple_build,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def climate_controller(tmp_path: Path) -> Climate:
    ensure_climate_stub(str(tmp_path))
    Climate._instances.clear()
    climate = Climate.getInstance(str(tmp_path))

    with climate.locked():
        climate._observed_start_year = 2001
        climate._observed_end_year = 2002
        climate._climatestation = "station-x"
        climate._cligen_db = "legacy"
        climate._adjust_mx_pt5 = False
        climate._silent_pass_observed_quality_guard = True
        climate._use_gridmet_wind_when_applicable = False
        climate._climate_mode = 9
        climate._climate_spatialmode = 2
        climate._test_unrelated = "BASE"
        climate.monthlies = [0.0]
        climate.cli_fn = "old.cli"
        climate.par_fn = "old.par"
        climate.sub_par_fns = {"ws": "old.prn"}
        climate.sub_cli_fns = {"ws": "old.cli"}

    # Prime the serialized signature fields so the following rewrite isolates
    # the same-size interleaving rather than first-write metadata growth.
    with climate.locked():
        pass

    yield climate
    Climate._instances.clear()


def _result() -> ClimateMultipleBuildResult:
    return ClimateMultipleBuildResult(
        monthlies=[1.0] * 12,
        cli_fn="wepp.cli",
        par_fn="station.par",
        sub_par_fns={"ws": "generated.prn"},
        sub_cli_fns={"ws": "generated.cli"},
        input_years=2,
        quality_guard_bypassed=False,
    )


def _same_size_rewrite(climate: Climate, field_name: str, value: object) -> object:
    """Inject one same-size atomic disk edit without reserializing metadata."""
    path = Path(climate._nodb)
    before = path.stat()
    payload = path.read_text(encoding="utf-8")
    old_value = json.dumps(getattr(climate, field_name))
    new_value = json.dumps(value)
    assert len(old_value.encode("utf-8")) == len(new_value.encode("utf-8"))
    pattern = rf'({re.escape(json.dumps(field_name))}\s*:\s*){re.escape(old_value)}'
    rewritten, count = re.subn(pattern, lambda match: match[1] + new_value, payload)
    assert count == 1

    # Real NoDb writes also serialize signature metadata, whose timestamp width
    # varies. This test needs an exact same-size interleaving, not that serializer.
    replacement = path.with_suffix(".replacement")
    replacement.write_text(rewritten, encoding="utf-8")
    os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
    os.replace(replacement, path)
    after = path.stat()
    assert before.st_size == after.st_size
    assert before.st_mtime != after.st_mtime
    return value


def test_unrelated_same_size_rewrite_is_preserved_during_finalization(
    climate_controller: Climate,
) -> None:
    snapshot = capture_multiple_build_inputs(climate_controller)
    unrelated_value = _same_size_rewrite(climate_controller, "_test_unrelated", "KEEP")

    finalize_multiple_build(climate_controller, snapshot, _result())

    current = Climate.load_detached(climate_controller.wd)
    assert current._test_unrelated == unrelated_value
    assert current.monthlies == [1.0] * 12
    assert current.cli_fn == "wepp.cli"
    assert current.par_fn == "station.par"
    assert current.sub_par_fns == {"ws": "generated.prn"}
    assert current.sub_cli_fns == {"ws": "generated.cli"}


@pytest.mark.parametrize("field_name,value", [("_climatestation", "station-y")])
def test_relevant_same_size_rewrite_supersedes_collected_outputs(
    climate_controller: Climate,
    field_name: str,
    value: object,
) -> None:
    snapshot = capture_multiple_build_inputs(climate_controller)
    _same_size_rewrite(climate_controller, field_name, value)

    with pytest.raises(ClimateMultipleBuildSupersededError) as exc_info:
        finalize_multiple_build(climate_controller, snapshot, _result())

    assert field_name.lstrip("_") in str(exc_info.value)
    current = Climate.load_detached(climate_controller.wd)
    assert current.monthlies == [0.0]
    assert current.cli_fn == "old.cli"
    assert current._test_unrelated == "BASE"


def test_malformed_relevant_rewrite_is_superseded_without_mutation(
    climate_controller: Climate,
) -> None:
    snapshot = capture_multiple_build_inputs(climate_controller)
    malformed_value = _same_size_rewrite(climate_controller, "_observed_start_year", None)

    with pytest.raises(ClimateMultipleBuildSupersededError, match="malformed climate inputs"):
        finalize_multiple_build(climate_controller, snapshot, _result())

    current = Climate.load_detached(climate_controller.wd)
    assert current._observed_start_year is malformed_value
    assert current.cli_fn == "old.cli"
