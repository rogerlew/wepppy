"""Direct single-storm CLIGEN generation helpers."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Optional

from wepppy.climates.cligen import (
    CligenStationsManager,
    ClimateFile,
    _bin_dir,
)

__all__ = ["SingleStormResult", "build_single_storm_cli"]


@dataclass(frozen=True)
class SingleStormResult:
    """Outcome of a single-storm CLIGEN build."""

    cli_path: Path
    par_path: Path
    monthlies: Optional[Dict[str, Dict[str, float]]]

    @property
    def cli_fn(self) -> str:
        return self.cli_path.name

    @property
    def par_fn(self) -> str:
        return self.par_path.name


def build_single_storm_cli(
    par: str | int,
    storm_date: str,
    design_storm_amount_inches: float,
    duration_of_storm_in_hours: float,
    time_to_peak_intensity_pct: float,
    max_intensity_inches_per_hour: float,
    *,
    output_dir: str,
    filename_prefix: Optional[str] = None,
    cliver: str | float = "5.3",
    version: str = "2015",
    timeout: float = 3.0,
) -> SingleStormResult:
    """Generate a CLIGEN file describing a synthetic single storm."""

    dest_dir = Path(output_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    par_id = str(par)
    prefix = filename_prefix or par_id
    target_par_name = f"{prefix}.par"
    target_cli_name = f"{prefix}.cli"
    target_par_path = dest_dir / target_par_name
    target_cli_path = dest_dir / target_cli_name

    cliver_str = _normalize_cliver(cliver)
    storm_date_str = _normalize_storm_date(storm_date)
    total_inches = float(design_storm_amount_inches)
    duration_hours = float(duration_of_storm_in_hours)
    peak_pct = float(time_to_peak_intensity_pct)
    max_intensity = float(max_intensity_inches_per_hour)

    if total_inches <= 0:
        raise ValueError("design_storm_amount_inches must be > 0")
    if duration_hours <= 0:
        raise ValueError("duration_of_storm_in_hours must be > 0")
    if not 0 < peak_pct < 100:
        raise ValueError("time_to_peak_intensity_pct must be between 0 and 100")
    if max_intensity <= 0:
        raise ValueError("max_intensity_inches_per_hour must be > 0")

    station_manager = CligenStationsManager(version=version)
    station_meta = station_manager.get_station_fromid(par_id)
    if station_meta is None:
        raise ValueError(f"CLIGEN station {par_id} not found in version {version}")

    par_contents = Path(station_meta.parpath).read_text()

    with TemporaryDirectory(prefix="wepppy_cligen_single_storm_") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        par_fn = f"{par_id}.par"
        cli_fn = "wepp.cli"

        tmp_par_path = tmpdir / par_fn
        tmp_par_path.write_text(par_contents)

        clinp_path = _write_clinp(
            tmpdir=tmpdir,
            par_fn=par_fn,
            cli_fn=cli_fn,
            cliver=cliver_str,
            storm_date=storm_date_str,
            design_inches=total_inches,
            duration_hours=duration_hours,
            time_to_peak_fraction=peak_pct * 0.01,
            max_intensity=max_intensity,
        )

        _run_cligen(
            tmpdir=tmpdir,
            cliver=cliver_str,
            par_fn=par_fn,
            clinp_path=clinp_path,
            timeout=timeout,
        )

        tmp_cli_path = tmpdir / cli_fn
        if not tmp_cli_path.exists():
            raise RuntimeError("CLIGEN did not produce the expected CLI file")

        shutil.copyfile(tmp_par_path, target_par_path)
        shutil.copyfile(tmp_cli_path, target_cli_path)

    monthlies: Optional[Dict[str, Dict[str, float]]] = None
    try:
        cli = ClimateFile(str(target_cli_path))
        monthlies = cli.calc_monthlies()
    except Exception:
        monthlies = None

    return SingleStormResult(
        cli_path=target_cli_path,
        par_path=target_par_path,
        monthlies=monthlies,
    )


def _normalize_storm_date(value: str) -> str:
    tokens = [token for token in re.split(r"[-/.\s]+", value.strip()) if token]
    if len(tokens) != 3:
        raise ValueError(f"storm_date must have three components, got {value!r}")

    month, day, year = (int(token) for token in tokens)
    if not 1 <= month <= 12:
        raise ValueError("storm_date month must be between 1 and 12")
    if not 1 <= day <= 31:
        raise ValueError("storm_date day must be between 1 and 31")
    if year <= 0:
        raise ValueError("storm_date year must be positive")

    return f"{month} {day} {year}"


def _normalize_cliver(value: str | float) -> str:
    if isinstance(value, (int, float)):
        value = f"{value:.1f}"
    value_str = str(value)
    if value_str == "4.3":
        return "4.3"
    if value_str == "5.2":
        return "5.2"
    return "5.3"


def _write_clinp(
    *,
    tmpdir: Path,
    par_fn: str,
    cli_fn: str,
    cliver: str,
    storm_date: str,
    design_inches: float,
    duration_hours: float,
    time_to_peak_fraction: float,
    max_intensity: float,
) -> Path:
    clinp_path = tmpdir / "clinp.txt"
    with clinp_path.open("w") as fid:
        if cliver == "4.3":
            fid.write(f"\n{par_fn}\nn\n")

        fid.write(
            "4\n"
            f"{storm_date}\n"
            f"{design_inches}\n"
            f"{duration_hours}\n"
            f"{time_to_peak_fraction}\n"
            f"{max_intensity}\n"
            f"{cli_fn}\n"
            "n\n\n"
        )
    return clinp_path


def _run_cligen(
    *,
    tmpdir: Path,
    cliver: str,
    par_fn: str,
    clinp_path: Path,
    timeout: float,
) -> None:
    if cliver == "4.3":
        cmd = [str(Path(_bin_dir) / "cligen43")]
    elif cliver == "5.2":
        cmd = [str(Path(_bin_dir) / "cligen52"), f"-i{par_fn}"]
    else:
        cmd = [str(Path(_bin_dir) / "cligen532"), f"-i{par_fn}"]

    log_path = tmpdir / "cligen.log"
    with clinp_path.open("rb") as clinp, log_path.open("wb") as log_fp:
        try:
            subprocess.run(
                cmd,
                stdin=clinp,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=timeout,
                cwd=tmpdir,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"CLIGEN timed out running command: {cmd}") from exc
        except subprocess.CalledProcessError as exc:
            log_tail = log_path.read_text() if log_path.exists() else ""
            raise RuntimeError(
                f"CLIGEN exited with {exc.returncode}; command: {cmd}\n{log_tail}"
            ) from exc
