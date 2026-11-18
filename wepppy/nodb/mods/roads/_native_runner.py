"""Roads native contributor execution with explicit facade-owned runner dependencies."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional


def _run_segment_hillslope(
    self,
    *,
    segment_run_id: int,
    climate_wepp_id: int,
    sim_years: int,
    wepp_bin: Optional[str],
    single_ofe_management_path: Path,
    single_ofe_soil_path: Path,
    single_ofe_slope_path: Path,
    make_hillslope_run,
    run_hillslope,
) -> None:
    baseline_runs_dir = Path(self.wepp_instance.runs_dir)
    climate_source = baseline_runs_dir / f"p{int(climate_wepp_id)}.cli"
    if not climate_source.exists():
        raise FileNotFoundError(
            f"Roads segment run requires baseline climate file: {climate_source}"
        )

    runs_dir = Path(self.roads_runs_dir)
    segment_cli_path = runs_dir / f"p{segment_run_id}.cli"
    segment_man_path = runs_dir / f"p{segment_run_id}.man"
    segment_sol_path = runs_dir / f"p{segment_run_id}.sol"
    segment_slp_path = runs_dir / f"p{segment_run_id}.slp"

    self._safe_link_or_copy(str(climate_source), str(segment_cli_path))

    if single_ofe_management_path.resolve() != segment_man_path.resolve():
        shutil.copy2(single_ofe_management_path, segment_man_path)
    if single_ofe_soil_path.resolve() != segment_sol_path.resolve():
        shutil.copy2(single_ofe_soil_path, segment_sol_path)
    if single_ofe_slope_path.resolve() != segment_slp_path.resolve():
        shutil.copy2(single_ofe_slope_path, segment_slp_path)

    if self._saved_parameterization_state() is not None:
        readbacks = getattr(self, "_parameterization_runtime_readbacks", {})
        source_record = readbacks.get(str(single_ofe_soil_path))
        if source_record is None:
            raise ValueError("Roads native soil has no parameterization readback.")
        readbacks[str(segment_sol_path)] = source_record
        self._record_parameterization_inputs(segment_sol_path, segment_slp_path, segment_man_path)

    make_hillslope_run(
        segment_run_id,
        sim_years,
        str(runs_dir),
        reveg=False,
        pass_family=self.wepp_instance.pass_family,
        wepp_bin=wepp_bin,
    )
    run_hillslope(segment_run_id, str(runs_dir), wepp_bin=wepp_bin)
