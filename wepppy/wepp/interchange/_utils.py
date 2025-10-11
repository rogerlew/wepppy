import time
from os.path import exists as _exists
from pathlib import Path
from datetime import datetime, timedelta

def _wait_for_path(path: Path, timeout=60.0, poll=0.5):
    """
    Wait for ``path`` to become available before attempting to read it.
    Dockerized deployments occasionally surface slower I/O, so give the
    filesystem a chance to catch up before raising.
    """
    deadline = time.time() + timeout

    while True:
        if path.exists():
            return

        if time.time() >= deadline:
            raise FileNotFoundError(
                f'Expected file {path} to be available within {timeout}s'
            )

        time.sleep(poll)

def _parse_float(token: str) -> float:
    stripped = token.strip()
    if not stripped:
        return 0.0
    if stripped[0] == ".":
        stripped = f"0{stripped}"
    try:
        return float(stripped)
    except ValueError:
        if "E" not in stripped.upper():
            if "-" in stripped[1:]:
                return float(stripped.replace("-", "E-", 1))
            if "+" in stripped[1:]:
                return float(stripped.replace("+", "E+", 1))
        return float(stripped)


def _julian_to_calendar(year: int, julian: int) -> tuple[int, int]:
    base = datetime(year, 1, 1) + timedelta(days=julian - 1)
    return base.month, base.day
