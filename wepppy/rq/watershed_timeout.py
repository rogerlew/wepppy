"""WRT-01: finite continuous watershed budgets from the workload being executed."""
from __future__ import annotations

from numbers import Integral
from pathlib import Path
import re
from typing import Any

__all__ = ["watershed_timeout_options"]
_MAX_RUN_BYTES = 1024 * 1024
_MAX_TIMEOUT_SECONDS = 2**31 - 1


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,10}", value.strip()):
        value = int(value.strip())
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"Watershed timeout requires a positive integer {name}.")
    return int(value)


def _prepared_workload(runs_dir: str) -> tuple[int, int]:
    # No-prep runs consume checked-out artifacts, not potentially newer NoDb settings.
    with (Path(runs_dir) / "pw0.run").open("rb") as stream:
        raw = stream.read(_MAX_RUN_BYTES + 1)
    if len(raw) > _MAX_RUN_BYTES:
        raise ValueError("Watershed timeout input pw0.run exceeds 1 MiB.")
    lines = [part for line in raw.decode("utf-8-sig").splitlines()
             if (part := line.partition("#")[0].strip())]
    if len(lines) < 7 or lines[2:4] != ["1", "2"]:
        raise ValueError("Watershed timeout requires a continuous mode-2 pw0.run.")
    # Modern binaries omit the legacy master-pass filename before the hillslope count.
    count_index = 4 if re.fullmatch(r"[0-9]+", lines[4]) else 5
    hillslopes = _positive_integer(lines[count_index], "prepared hillslope count")
    # Anchor the workload to the owned layout; a truncated file or an extra
    # trailing integer must not masquerade as a different workload.
    block_end = count_index + 1 + 3 * hillslopes
    if block_end > len(lines) - 8 or lines[-4:-1] != ["pw0.cli", "pw0.sol", "0"]:
        raise ValueError("Watershed timeout requires intact pw0.run workload records.")
    if (lines[block_end:block_end + 2] != ["Yes", "No"] or
            any(lines[i:i + 2] != ["M", "Y"]
                for i in range(count_index + 1, block_end, 3))):
        raise ValueError("Watershed timeout requires intact pw0.run hillslope records.")
    years = _positive_integer(lines[-1], "prepared simulation years")
    return years, hillslopes


def watershed_timeout_options(
    wepp: Any, climate: Any, base_timeout: int, *, prepared_inputs: bool = False,
) -> dict[str, Any]:
    """Return enqueue timeout/metadata; single-storm calls retain existing behavior."""
    if climate.is_single_storm:
        return {"timeout": base_timeout}
    if prepared_inputs:
        years, hillslopes = _prepared_workload(wepp.runs_dir)
        source = "prepared_run_file"
    else:
        years = _positive_integer(climate.input_years, "simulation years")
        hillslopes = _positive_integer(wepp.watershed_instance.sub_n, "hillslope count")
        source = "controllers"
    base_timeout = _positive_integer(base_timeout, "base timeout")
    # 0.05 seconds / 3600 seconds per hour = 1 / 72000. Integer arithmetic
    # keeps exact hour boundaries stable without float rounding or overflow.
    hours = max(12, (years * hillslopes + 71999) // 72000)
    timeout = max(base_timeout, hours * 3600)
    if timeout > _MAX_TIMEOUT_SECONDS:
        raise ValueError("Watershed timeout exceeds the supported RQ alarm range.")
    return {"timeout": timeout, "meta": {"watershed_timeout": {
        "policy": "WRT-01", "years": years, "hillslopes": hillslopes,
        "seconds_per_hillslope_year": 0.05, "timeout_seconds": timeout,
        "workload_source": source, "wepp_bin": wepp.wepp_bin,
    }}}
