"""Roads modeled-area accounting and report resource regeneration."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List

from wepppy.project_assets import WEPP_LOSS_HILL

def _build_roads_segment_loss_summary_parquet(self, *, interchange_dir: Path) -> str:
    from ._segment_loss_summary import build_segment_loss_summary

    def execution_calendar():
        climate = self.wepp_instance.climate_instance
        return climate.input_years, climate.calendar_start_year

    return build_segment_loss_summary(
        Path(self.wd), interchange_dir, execution_calendar=execution_calendar,
    )


def _required_roads_report_resource_relpaths(
    self,
    *,
    is_single_storm: bool,
    include_chnwb: bool,
    include_segment_loss_summary: bool,
) -> List[str]:
    base = os.path.join("wepp", "roads", "output", "interchange")
    required = [
        os.path.join(base, "H.pass.parquet"),
        os.path.join(base, "ebe_pw0.parquet"),
        os.path.join(base, "README.md"),
    ]
    if not is_single_storm:
        required.extend(
            [
                os.path.join(base, "H.wat.parquet"),
                os.path.join(base, "loss_pw0.out.parquet"),
                WEPP_LOSS_HILL.relative_path("roads"),
                os.path.join(base, "loss_pw0.chn.parquet"),
                os.path.join(base, "totalwatsed3.parquet"),
            ]
        )
        if include_segment_loss_summary:
            required.append(os.path.join(base, "roads_segment_loss_summary.parquet"))
        if include_chnwb:
            required.append(os.path.join(base, "chnwb.parquet"))
    return required


def _regenerate_roads_report_resources(self) -> Dict[str, Any]:
    from wepppy.nodb.wepp_nodb_post_utils import activate_query_engine_for_run
    from wepppy.wepp.interchange import (
        generate_interchange_documentation,
        run_totalwatsed3,
        run_wepp_hillslope_interchange,
        run_wepp_watershed_interchange,
    )

    from wepppy.wepp.interchange.roads_accounting import LEDGER, has_accounting, load, regenerate, validate_destinations

    validate_destinations(Path(self.wd))
    corrected = has_accounting(Path(self.wd))
    if corrected:
        load(Path(self.wd))
    climate = self.wepp_instance.climate_instance
    is_single_storm = bool(getattr(climate, "is_single_storm", False))
    start_year_raw = getattr(climate, "calendar_start_year", None)
    start_year = int(start_year_raw) if start_year_raw not in (None, "") else None
    output_dir = Path(self.roads_output_dir)
    interchange_dir = output_dir / "interchange"
    hillslope_soil_available = any(output_dir.glob("H*.soil.dat"))
    watershed_soil_available = (output_dir / "soil_pw0.txt").exists()
    chan_out_available = (output_dir / "chan.out").exists() or (output_dir / "chan.out.gz").exists()
    chnwb_available = (output_dir / "chnwb.txt").exists() or (output_dir / "chnwb.txt.gz").exists()
    run_hillslope_soil_interchange = not is_single_storm and hillslope_soil_available
    run_watershed_soil_interchange = not is_single_storm and watershed_soil_available
    run_chan_out_interchange = not is_single_storm and chan_out_available
    run_chnwb_interchange = not is_single_storm and chnwb_available

    self._append_roads_log(
        "run",
        "roads_report_resources_regen_started",
        {
            "roads_output_relpath": os.path.relpath(output_dir, self.wd),
            "is_single_storm": is_single_storm,
            "start_year": start_year,
            "run_hillslope_soil_interchange": run_hillslope_soil_interchange,
            "run_watershed_soil_interchange": run_watershed_soil_interchange,
            "run_chan_out_interchange": run_chan_out_interchange,
            "run_chnwb_interchange": run_chnwb_interchange,
        },
    )

    if corrected and not is_single_storm:
        # Source WAT/SOIL/ELEMENT were converted before allocation. Rewriting
        # them here would invalidate the ledger even for equal numeric rows.
        from wepppy.wepp.interchange import run_wepp_hillslope_pass_interchange

        run_wepp_hillslope_pass_interchange(output_dir, pass_family=self.wepp_instance.pass_family)
    else:
        run_wepp_hillslope_interchange(
            output_dir,
            pass_family=self.wepp_instance.pass_family,
            start_year=start_year,
            run_loss_interchange=not is_single_storm,
            run_soil_interchange=run_hillslope_soil_interchange and not corrected,
            run_wat_interchange=not is_single_storm and not corrected,
            delete_after_interchange=False,
        )
    self._append_roads_log(
        "run",
        "roads_hillslope_interchange_completed",
        {"interchange_relpath": os.path.relpath(interchange_dir, self.wd)},
    )

    if not is_single_storm:
        baseflow_opts = getattr(self.wepp_instance, "baseflow_opts", None)
        if baseflow_opts is None:
            from wepppy.nodb.core.wepp import BaseflowOpts

            baseflow_opts = BaseflowOpts()
        if corrected:
            regenerate(Path(self.wd), baseflow_opts)
        else:
            run_totalwatsed3(interchange_dir, baseflow_opts=baseflow_opts)
        self._append_roads_log(
            "run",
            "roads_totalwatsed3_completed",
            {"totalwatsed3_relpath": os.path.relpath(interchange_dir / "totalwatsed3.parquet", self.wd)},
        )

    run_wepp_watershed_interchange(
        output_dir,
        pass_family=self.wepp_instance.pass_family,
        start_year=start_year,
        run_chan_out_interchange=run_chan_out_interchange,
        run_soil_interchange=run_watershed_soil_interchange,
        run_chnwb_interchange=run_chnwb_interchange,
        delete_after_interchange=False,
    )
    self._append_roads_log(
        "run",
        "roads_watershed_interchange_completed",
        {"interchange_relpath": os.path.relpath(interchange_dir, self.wd)},
    )

    roads_segment_loss_summary_relpath = None
    if not is_single_storm:
        roads_segment_loss_summary_relpath = self._build_roads_segment_loss_summary_parquet(
            interchange_dir=interchange_dir
        )
        self._append_roads_log(
            "run",
            "roads_segment_loss_summary_parquet_completed",
            {"roads_segment_loss_summary_relpath": roads_segment_loss_summary_relpath},
        )

    generate_interchange_documentation(interchange_dir)
    self._append_roads_log(
        "run",
        "roads_interchange_readme_completed",
        {"readme_relpath": os.path.relpath(interchange_dir / "README.md", self.wd)},
    )

    activate_query_engine_for_run(self.wepp_instance)
    self._append_roads_log("run", "roads_query_engine_catalog_refreshed")

    required_relpaths = self._required_roads_report_resource_relpaths(
        is_single_storm=is_single_storm,
        include_chnwb=run_chnwb_interchange,
        include_segment_loss_summary=not is_single_storm,
    )
    if corrected and not is_single_storm:
        from wepppy.wepp.interchange.roads_accounting import accounting_source

        accounting_source(Path(self.wd))
        required_relpaths.append("wepp/roads/output/interchange/H.accounting.wat.parquet")
    if corrected:
        required_relpaths.append(str(LEDGER))
    missing_relpaths = [relpath for relpath in required_relpaths if not Path(self.wd, relpath).exists()]
    if missing_relpaths:
        self._append_roads_log(
            "run",
            "roads_report_resources_missing",
            {"missing_relpaths": missing_relpaths},
        )
        missing = ", ".join(missing_relpaths)
        raise FileNotFoundError(
            f"Roads report resource regeneration incomplete; missing required resources: {missing}"
        )

    resources = {
        "is_single_storm": is_single_storm,
        "status": "ready",
        "output_scope": "roads",
        "accounting_policy": "roads_modeled_area_v1" if corrected else "historical_unverified",
        "roads_output_relpath": os.path.relpath(output_dir, self.wd),
        "interchange_relpath": os.path.relpath(interchange_dir, self.wd),
        "required_relpaths": required_relpaths,
        "missing_relpaths": [],
        "roads_segment_loss_summary_relpath": roads_segment_loss_summary_relpath,
        "generated_at": int(time.time()),
    }
    self._append_roads_log(
        "run",
        "roads_report_resources_regen_completed",
        {
            "required_resource_count": len(required_relpaths),
            "interchange_relpath": resources["interchange_relpath"],
        },
    )
    return resources


def _prepare_modeled_area_accounting(self, canonical_ids, records):
    from wepppy.wepp.interchange import run_wepp_hillslope_interchange
    from wepppy.wepp.interchange.roads_accounting import compose, validate_destinations

    validate_destinations(Path(self.wd))
    climate = self.wepp_instance.climate_instance
    is_single_storm = bool(getattr(climate, "is_single_storm", False))
    if not is_single_storm:
        start_year_raw = getattr(climate, "calendar_start_year", None)
        run_wepp_hillslope_interchange(
            Path(self.roads_output_dir),
            pass_family=self.wepp_instance.pass_family,
            start_year=int(start_year_raw) if start_year_raw not in (None, "") else None,
            run_loss_interchange=True,
            run_soil_interchange=any(Path(self.roads_output_dir).glob("H*.soil.dat")),
            run_wat_interchange=True,
            delete_after_interchange=False,
        )
    return compose(Path(self.wd), canonical_ids, records, single_storm=is_single_storm)
