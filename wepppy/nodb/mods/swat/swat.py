"""SWAT+ NoDb controller.

Implements recall generation, TxtInOut assembly, and SWAT+ execution for
WEPP hillslope pass routing through SWAT-DEG channels.
"""

from __future__ import annotations

import csv
import importlib
import json
import os
import shutil
import signal
import subprocess
import time
from collections import deque
from datetime import datetime
from os.path import exists as _exists
from os.path import join as _join
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb

from wepppy.nodb.mods.swat.print_prt import PRINT_PRT_DAILY, PrintPrtConfig, load_print_prt
from wepppy.nodb.base import NoDbBase
from wepppy.topo.peridot.peridot_runner import read_network
from wepppy.wepp.interchange._rust_interchange import resolve_cli_calendar_path, version_args
from wepppy.wepp.interchange._utils import CalendarLookup, _build_cli_calendar_lookup, _julian_to_calendar
from wepppy.nodb.status_messenger import StatusMessenger

__all__ = [
    'SwatNoDbLockedException',
    'Swat',
]


class SwatNoDbLockedException(Exception):
    pass


class Swat(NoDbBase):
    __name__ = 'Swat'

    @classmethod
    def _post_instance_loaded(cls, instance: "Swat") -> "Swat":
        if not hasattr(instance, "force_time_start_year"):
            instance.force_time_start_year = False
        if not hasattr(instance, "width_fallback"):
            instance.width_fallback = "error"
        if not hasattr(instance, "netw_area_units"):
            instance.netw_area_units = "auto"
        if not hasattr(instance, "include_baseflow"):
            instance.include_baseflow = True
        if not hasattr(instance, "_recall_calendar_lookup"):
            instance._recall_calendar_lookup = None
        if not hasattr(instance, "_recall_calendar_ready"):
            instance._recall_calendar_ready = False
        if not hasattr(instance, "print_prt"):
            instance.print_prt = instance._load_print_prt_template() or PrintPrtConfig()
        if not hasattr(instance, "print_prt_template_dir"):
            instance.print_prt_template_dir = instance.template_dir
        if not hasattr(instance, "print_prt_defaults_applied"):
            instance._apply_print_prt_defaults(instance.print_prt)
            instance.print_prt_defaults_applied = True
        if not hasattr(instance, "swat_interchange_enabled"):
            instance.swat_interchange_enabled = True
        if not hasattr(instance, "swat_interchange_chunk_rows"):
            instance.swat_interchange_chunk_rows = 100_000
        if not hasattr(instance, "swat_interchange_ncpu"):
            instance.swat_interchange_ncpu = None
        if not hasattr(instance, "swat_interchange_compression"):
            instance.swat_interchange_compression = "snappy"
        if not hasattr(instance, "swat_interchange_write_manifest"):
            instance.swat_interchange_write_manifest = True
        if not hasattr(instance, "swat_interchange_delete_manifest"):
            instance.swat_interchange_delete_manifest = False
        if not hasattr(instance, "swat_interchange_delete_after_interchange"):
            instance.swat_interchange_delete_after_interchange = False
        if not hasattr(instance, "swat_interchange_dry_run"):
            instance.swat_interchange_dry_run = False
        if not hasattr(instance, "swat_interchange_fail_fast"):
            instance.swat_interchange_fail_fast = False
        if not hasattr(instance, "swat_interchange_overwrite"):
            instance.swat_interchange_overwrite = False
        if not hasattr(instance, "swat_interchange_stale_after_hours"):
            instance.swat_interchange_stale_after_hours = None
        if not hasattr(instance, "swat_interchange_include"):
            instance.swat_interchange_include = []
        if not hasattr(instance, "swat_interchange_exclude"):
            instance.swat_interchange_exclude = []
        if not hasattr(instance, "swat_interchange_summary"):
            instance.swat_interchange_summary = None
        if not hasattr(instance, "last_swat_interchange_at"):
            instance.last_swat_interchange_at = None
        if not hasattr(instance, "swat_interchange_status"):
            instance.swat_interchange_status = "idle"
        return instance

    filename = 'swat.nodb'

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self.enabled = bool(self.config_get_bool('swat', 'enabled', True))
            self.swatplus_version_major = int(
                self.config_get_int('swat', 'swatplus_version_major', 1)
            )
            self.swatplus_version_minor = int(
                self.config_get_int('swat', 'swatplus_version_minor', 4)
            )

            self.swat_bin = self._resolve_swat_bin()
            self.template_dir = self._resolve_template_dir()
            self.recall_filename_template = self.config_get_str(
                'swat', 'recall_filename_template', 'hill_{wepp_id:05d}.rec'
            )
            self.recall_subdir = self.config_get_str('swat', 'recall_subdir', 'recall')
            self.recall_wst = self.config_get_str('swat', 'recall_wst', 'wea1')
            self.recall_object_type = self.config_get_str('swat', 'recall_object_type', 'sdc')
            self.include_subsurface = bool(
                self.config_get_bool('swat', 'include_subsurface', True)
            )
            self.include_tile = bool(self.config_get_bool('swat', 'include_tile', True))
            self.include_baseflow = bool(self.config_get_bool('swat', 'include_baseflow', True))
            self.cli_calendar_path = self.config_get_path('swat', 'cli_calendar_path', None)
            if isinstance(self.cli_calendar_path, str) and self.cli_calendar_path.lower() == "none":
                self.cli_calendar_path = None
            self.time_start_year = int(self.config_get_int('swat', 'time_start_year', 1))
            self.force_time_start_year = bool(
                self.config_get_bool('swat', 'force_time_start_year', False)
            )
            self.width_method = self.config_get_str('swat', 'width_method', 'bieger2015').lower()
            self.width_fallback = self.config_get_str('swat', 'width_fallback', 'error').lower()
            self.netw_area_units = self.config_get_str('swat', 'netw_area_units', 'auto').lower()
            self.disable_aquifer = bool(
                self.config_get_bool('swat', 'disable_aquifer', True)
            )
            self.qswat_wm = float(self.config_get_float('swat', 'qswat_wm', 1.0))
            self.qswat_we = float(self.config_get_float('swat', 'qswat_we', 0.5))
            self.qswat_dm = float(self.config_get_float('swat', 'qswat_dm', 0.5))
            self.qswat_de = float(self.config_get_float('swat', 'qswat_de', 0.4))
            self.swat_interchange_enabled = bool(
                self.config_get_bool('swat', 'swat_interchange_enabled', True)
            )
            self.swat_interchange_chunk_rows = int(
                self.config_get_int('swat', 'swat_interchange_chunk_rows', 100_000)
            )
            self.swat_interchange_ncpu = self.config_get_int('swat', 'swat_interchange_ncpu', None)
            self.swat_interchange_compression = self.config_get_str(
                'swat', 'swat_interchange_compression', 'snappy'
            )
            self.swat_interchange_write_manifest = bool(
                self.config_get_bool('swat', 'swat_interchange_write_manifest', True)
            )
            self.swat_interchange_delete_manifest = bool(
                self.config_get_bool('swat', 'swat_interchange_delete_manifest', False)
            )
            delete_after = self.config_get_bool(
                'swat', 'swat_interchange_delete_after_interchange', None
            )
            if delete_after is None:
                delete_after = self.config_get_bool(
                    'interchange', 'delete_after_interchange', False
                )
            self.swat_interchange_delete_after_interchange = bool(delete_after)
            self.swat_interchange_dry_run = bool(
                self.config_get_bool('swat', 'swat_interchange_dry_run', False)
            )
            self.swat_interchange_fail_fast = bool(
                self.config_get_bool('swat', 'swat_interchange_fail_fast', False)
            )
            self.swat_interchange_overwrite = bool(
                self.config_get_bool('swat', 'swat_interchange_overwrite', False)
            )
            self.swat_interchange_stale_after_hours = self.config_get_float(
                'swat', 'swat_interchange_stale_after_hours', None
            )
            self.swat_interchange_include = self.config_get_list(
                'swat', 'swat_interchange_include', []
            )
            self.swat_interchange_exclude = self.config_get_list(
                'swat', 'swat_interchange_exclude', []
            )

            self.channel_params: Dict[str, Any] = {
                'mann': self.config_get_float('swat', 'channel_mann', 0.05),
                'fpn': self.config_get_float('swat', 'channel_fpn', None),
                'erod_fact': self.config_get_float('swat', 'channel_erod_fact', 0.01),
                'cov_fact': self.config_get_float('swat', 'channel_cov_fact', 0.01),
                'd50_mm': self.config_get_float('swat', 'channel_d50_mm', 12.0),
            }

            self.recall_manifest: Optional[List[Dict[str, Any]]] = None
            self.build_summary: Optional[dict] = None
            self.last_build_at: Optional[str] = None
            self.run_summary: Optional[dict] = None
            self.last_run_at: Optional[str] = None
            self.status: str = 'idle'
            self.swat_interchange_summary: Optional[dict] = None
            self.last_swat_interchange_at: Optional[str] = None
            self.swat_interchange_status: str = "idle"
            self._recall_calendar_lookup: Optional[CalendarLookup] = None
            self._recall_calendar_ready = False
            self.print_prt_template_dir: Optional[str] = None
            self.print_prt = self._load_print_prt_template() or PrintPrtConfig()
            if self.print_prt_template_dir is None:
                self.print_prt_template_dir = self.template_dir
            self._apply_print_prt_defaults(self.print_prt)
            self.print_prt_defaults_applied = True

            os.makedirs(self.swat_dir, exist_ok=True)
            os.makedirs(self.swat_txtinout_dir, exist_ok=True)
            os.makedirs(self.swat_recall_dir, exist_ok=True)
            os.makedirs(self.swat_manifests_dir, exist_ok=True)
            os.makedirs(self.swat_logs_dir, exist_ok=True)
            os.makedirs(self.swat_outputs_dir, exist_ok=True)

    @property
    def swat_dir(self) -> str:
        return _join(self.wd, 'swat')

    @property
    def swat_txtinout_dir(self) -> str:
        return _join(self.swat_dir, 'TxtInOut')

    @property
    def swat_recall_dir(self) -> str:
        if not self.recall_subdir:
            return self.swat_txtinout_dir
        return _join(self.swat_txtinout_dir, self.recall_subdir)

    @property
    def swat_manifests_dir(self) -> str:
        return _join(self.swat_dir, 'manifests')

    @property
    def swat_logs_dir(self) -> str:
        return _join(self.swat_dir, 'logs')

    @property
    def swat_outputs_dir(self) -> str:
        return _join(self.swat_dir, 'outputs')

    def build_recall_connections(self) -> List[Tuple[int, int]]:
        hillslopes_parquet = _join(self.wd, 'watershed', 'hillslopes.parquet')
        channels_parquet = _join(self.wd, 'watershed', 'channels.parquet')
        if not _exists(hillslopes_parquet):
            raise FileNotFoundError(f"Missing hillslopes parquet: {hillslopes_parquet}")
        if not _exists(channels_parquet):
            raise FileNotFoundError(f"Missing channels parquet: {channels_parquet}")

        with duckdb.connect() as con:
            hills_cols = _read_parquet_columns(con, hillslopes_parquet)
            chn_cols = _read_parquet_columns(con, channels_parquet)

            hills_topaz = _resolve_column(hills_cols, ('topaz_id', 'TopazID'), hillslopes_parquet)
            hills_wepp = _resolve_column(hills_cols, ('wepp_id', 'WeppID'), hillslopes_parquet)
            hills_chn_enum = _resolve_column_optional(
                hills_cols,
                (
                    'chn_enum',
                    'ChnEnum',
                    'channel_enum',
                    'channel_id',
                    'chn_id',
                    'channel',
                ),
            )
            hills_chn_topaz = _resolve_column_optional(
                hills_cols,
                (
                    'chn_topaz_id',
                    'channel_topaz_id',
                    'chn_topaz',
                    'channel_topaz',
                ),
            )
            chn_topaz = _resolve_column(chn_cols, ('topaz_id', 'TopazID'), channels_parquet)
            chn_enum = _resolve_column(chn_cols, ('chn_enum', 'ChnEnum'), channels_parquet)

            hills_rows = con.execute(
                "SELECT {topaz}, {wepp}, {chn_enum}, {chn_topaz} "
                "FROM read_parquet('{path}')".format(
                    topaz=_quote_ident(hills_topaz),
                    wepp=_quote_ident(hills_wepp),
                    chn_enum=_select_or_null(hills_chn_enum, "hills_chn_enum"),
                    chn_topaz=_select_or_null(hills_chn_topaz, "hills_chn_topaz"),
                    path=_escape_sql_path(hillslopes_parquet),
                )
            ).fetchall()
            chn_rows = con.execute(
                f"SELECT {chn_topaz}, {chn_enum} FROM read_parquet('{_escape_sql_path(channels_parquet)}')"
            ).fetchall()

        chn_lookup: Dict[int, int] = {}
        chn_enum_set: set[int] = set()
        for topaz_id, chn_id in chn_rows:
            if topaz_id is None or chn_id is None:
                continue
            topaz_id = int(topaz_id)
            chn_id = int(chn_id)
            chn_lookup[topaz_id] = chn_id
            chn_enum_set.add(chn_id)

        connections: List[Tuple[int, int]] = []
        used_heuristic = False
        missing: List[Tuple[int, int]] = []
        for topaz_id, wepp_id, hills_chn_enum_val, hills_chn_topaz_val in hills_rows:
            if topaz_id is None or wepp_id is None:
                continue
            topaz_id = int(topaz_id)
            wepp_id = int(wepp_id)
            chn_id: Optional[int] = None

            if hills_chn_enum_val is not None:
                try:
                    candidate = int(hills_chn_enum_val)
                except (TypeError, ValueError):
                    candidate = None
                if candidate is not None:
                    if candidate in chn_enum_set:
                        chn_id = candidate
                    elif candidate in chn_lookup:
                        chn_id = chn_lookup.get(candidate)

            if chn_id is None and hills_chn_topaz_val is not None:
                try:
                    candidate = int(hills_chn_topaz_val)
                except (TypeError, ValueError):
                    candidate = None
                if candidate is not None:
                    chn_id = chn_lookup.get(candidate)

            if chn_id is None:
                chn_topaz_id = topaz_id + (4 - (topaz_id % 10))
                chn_id = chn_lookup.get(chn_topaz_id)
                if chn_id is not None:
                    used_heuristic = True

            if chn_id is None:
                missing.append((wepp_id, topaz_id))
                continue

            connections.append((wepp_id, chn_id))

        if missing:
            sample = ", ".join(
                f"wepp_id={wepp_id}, topaz_id={topaz_id}" for wepp_id, topaz_id in missing[:8]
            )
            raise SwatNoDbLockedException(
                "Missing channel mapping for hillslopes (count={}). "
                "Check hillslopes.parquet for chn_enum/chn_topaz_id columns or provide "
                "channel mapping; sample: {}".format(len(missing), sample)
            )

        if used_heuristic:
            self.logger.warning(
                "SWAT build: derived channel mapping using TOPAZ id heuristic; "
                "set explicit channel columns in hillslopes.parquet to avoid ambiguity."
            )

        connections.sort(key=lambda item: item[0])
        return connections

    def build_inputs(self) -> Dict[str, Any]:
        if not self.enabled:
            raise SwatNoDbLockedException("SWAT mod is disabled in the run config.")

        summary: Dict[str, Any] = {}
        build_log = _join(self.swat_logs_dir, "swat_build.log")

        with self.locked():
            self.status = 'building'
            self._append_log(build_log, "START build_inputs")
            self.logger.info("SWAT build: copying template TxtInOut")

            self._ensure_print_prt_template_sync()
            self._prepare_txtinout()
            self._normalize_climate_nbyr()
            self._validate_recall_wst()
            summary["template_dir"] = self.template_dir
            summary["txtinout_dir"] = self.swat_txtinout_dir
            summary["recall_subdir"] = self.recall_subdir

            self.logger.info("SWAT build: generating recall inputs")
            recall_connections = self.build_recall_connections()
            summary["recall_connections"] = len(recall_connections)

            recall_manifest = self.build_recall(recall_connections)
            summary["recall_count"] = len(recall_manifest)
            self._normalize_recall_paths()
            self._align_recall_years()
            self._convert_wepp_recall_files()
            self._patch_recall_con_areas()

            self.logger.info("SWAT build: generating connectivity and channel inputs")
            channels = self.build_connectivity()
            summary["channel_count"] = len(channels)

            self.logger.info("SWAT build: patching TxtInOut metadata")
            time_range = self.patch_txtinout(recall_manifest, channels)
            if time_range is not None:
                summary["time_sim_range"] = {
                    "start_year": time_range[0],
                    "start_day": time_range[1],
                    "end_year": time_range[2],
                    "end_day": time_range[3],
                }

            self.validate(recall_manifest, channels)

            self.build_summary = summary
            self.last_build_at = datetime.utcnow().isoformat()
            self.status = 'ready'
            self._append_log(build_log, "COMPLETE build_inputs")

        return summary

    def enable_print_prt_daily_channel_outputs(self) -> None:
        """Enable daily outputs for basin water balance + channel routing."""
        with self.locked():
            if self.print_prt is None:
                self.print_prt = self._load_print_prt_template() or PrintPrtConfig()
                if self.print_prt_template_dir is None:
                    self.print_prt_template_dir = self.template_dir

            for object_name in ("basin_wb", "channel_sd", "hyd"):
                attr_name = object_name.replace("-", "_")
                if not hasattr(self.print_prt.objects, attr_name):
                    continue
                current = int(getattr(self.print_prt.objects, attr_name))
                self.print_prt.objects.set_mask(object_name, current | PRINT_PRT_DAILY)

    def build_recall(self, recall_connections: List[Tuple[int, int]]) -> List[Dict[str, Any]]:
        wepp_output_dir = _join(self.wd, 'wepp', 'output')
        if not _exists(wepp_output_dir):
            raise FileNotFoundError(f"Missing WEPP output directory: {wepp_output_dir}")

        module, err = _load_rust_swat_utils()
        if module is None:
            raise ModuleNotFoundError(
                "wepppyo3.swat_utils is required for SWAT recall generation."
            ) from err

        recall_func = getattr(module, "wepp_hillslope_pass_to_swat_recall", None)
        if recall_func is None:
            raise AttributeError(
                "wepppyo3.swat_utils is missing wepp_hillslope_pass_to_swat_recall"
            )

        version_major, version_minor = version_args()
        cli_calendar_path = self.cli_calendar_path
        if cli_calendar_path is None:
            cli_path = resolve_cli_calendar_path(
                Path(wepp_output_dir),
                cli_hint=None,
                log=self.logger,
            )
            if cli_path is not None:
                cli_calendar_path = str(cli_path)

        manifest = recall_func(
            wepp_output_dir,
            self.swat_txtinout_dir,
            version_major,
            version_minor,
            recall_subdir=self.recall_subdir,
            cli_calendar_path=cli_calendar_path,
            filename_template=self.recall_filename_template,
            include_subsurface=self.include_subsurface,
            include_tile=self.include_tile,
            include_baseflow=self.include_baseflow,
            recall_connections=recall_connections,
            recall_wst=self.recall_wst,
            recall_object_type=self.recall_object_type,
            ncpu=None,
            write_manifest=True,
        )

        recall_manifest = [] if manifest is None else list(manifest)
        manifest_path = _join(self.swat_manifests_dir, "recall_manifest.json")
        with open(manifest_path, "w") as handle:
            json.dump(recall_manifest, handle, indent=2)
        self.recall_manifest = recall_manifest
        return recall_manifest

    def build_connectivity(self) -> List[Dict[str, Any]]:
        channels = self._load_channels()
        if not channels:
            raise SwatNoDbLockedException("No channels found for SWAT connectivity build.")

        downstream_map = self._build_downstream_map(channels)
        self._write_chandeg_con(channels, downstream_map)
        self._write_channel_lte(channels)
        self._write_hyd_sed_lte(channels)
        return channels

    def patch_txtinout(
        self,
        recall_manifest: List[Dict[str, Any]],
        channels: List[Dict[str, Any]],
    ) -> Optional[Tuple[int, int, int, int]]:
        time_range = self._patch_time_sim(recall_manifest)
        channel_count = len(channels)
        recall_count = len(recall_manifest)
        total_area_ha = self._estimate_total_area_ha()
        self._patch_object_counts(channel_count, self._count_written_recall(recall_manifest), total_area_ha)
        self._write_print_prt()
        if self.disable_aquifer:
            self._patch_rout_unit_con()
        return time_range

    def run_swat(self, status_channel: Optional[str] = None) -> Dict[str, Any]:
        if not self.enabled:
            raise SwatNoDbLockedException("SWAT mod is disabled in the run config.")

        if not _exists(self.swat_bin):
            raise FileNotFoundError(f"Missing SWAT+ binary: {self.swat_bin}")

        if not _exists(self.swat_txtinout_dir):
            raise FileNotFoundError(f"Missing SWAT TxtInOut directory: {self.swat_txtinout_dir}")

        run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        run_dir = _join(self.swat_outputs_dir, f"run_{run_id}")
        os.makedirs(run_dir, exist_ok=True)
        log_path = _join(self.swat_logs_dir, f"swat_run_{run_id}.log")

        with self.locked():
            self.status = 'running'
            self.last_run_at = datetime.utcnow().isoformat()
            self.logger.info("SWAT run: starting SWAT+ binary")

        if status_channel is None:
            status_channel = self._status_channel

        stdout_tail_lines: deque[str] = deque(maxlen=20)
        stdout_bytes = 0

        start_time = time.time()
        returncode: Optional[int] = None

        with open(log_path, "w") as handle:
            process = subprocess.Popen(
                [self.swat_bin],
                cwd=self.swat_txtinout_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            try:
                while True:
                    line = process.stdout.readline() if process.stdout is not None else ""
                    if line == "" and process.poll() is not None:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    handle.write(line + "\n")
                    handle.flush()
                    stdout_bytes += len(line) + 1
                    stdout_tail_lines.append(line)
                    if status_channel:
                        StatusMessenger.publish(status_channel, line)
            finally:
                if process.stdout is not None:
                    process.stdout.close()
                returncode = process.wait()

        signal_name = _signal_name(returncode or 0)
        self.logger.info("SWAT run: SWAT+ exit code %s", returncode)
        if signal_name:
            self.logger.warning("SWAT run: SWAT+ terminated by signal %s", signal_name)

        stdout_tail = _tail_text("\n".join(stdout_tail_lines))
        stderr_tail = ""
        output_files = self._collect_run_outputs(start_time)
        manifest_rel = "files_out.out"
        manifest_src = _join(self.swat_txtinout_dir, manifest_rel)
        if _exists(manifest_src) and manifest_rel not in output_files:
            output_files.append(manifest_rel)
        copied = self._copy_outputs(output_files, run_dir)

        run_summary = {
            "run_id": run_id,
            "returncode": returncode,
            "signal": signal_name,
            "stdout_bytes": stdout_bytes,
            "stderr_bytes": 0,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "output_files": copied,
            "txtinout_dir": self.swat_txtinout_dir,
            "log_path": log_path,
        }

        with self.locked():
            self.run_summary = run_summary
            self.status = 'ready' if (returncode or 0) == 0 else 'error'
            self.logger.info("SWAT run: outputs archived under %s", run_dir)

        index_path = _join(run_dir, "index.json")
        with open(index_path, "w") as handle:
            json.dump(run_summary, handle, indent=2)

        if (returncode or 0) != 0:
            message = f"SWAT+ run failed with return code {returncode}"
            if signal_name:
                message += f" ({signal_name})"
            if stderr_tail:
                message += f"; stderr tail:\n{stderr_tail}"
            elif stdout_tail:
                message += f"; stdout tail:\n{stdout_tail}"
            message += f"\nSee log: {log_path}"
            raise RuntimeError(message)

        interchange_summary = None
        if self.swat_interchange_enabled:
            interchange_summary = self.run_swat_interchange(
                run_dir=run_dir,
                status_channel=status_channel,
            )
            if interchange_summary is not None:
                run_summary["interchange_summary"] = interchange_summary
                with open(index_path, "w") as handle:
                    json.dump(run_summary, handle, indent=2)
                with self.locked():
                    self.run_summary = run_summary
                    self.status = 'ready'

        return run_summary

    def run_swat_interchange(
        self,
        run_dir: Optional[str] = None,
        *,
        status_channel: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.swat_interchange_enabled:
            return None

        run_dir = self._resolve_latest_run_dir(run_dir)
        if run_dir is None:
            raise FileNotFoundError("No SWAT run directory found for interchange.")
        run_dir = os.path.abspath(run_dir)
        if not _exists(run_dir):
            raise FileNotFoundError(f"Missing SWAT run directory: {run_dir}")

        rust_mod, rust_err = _load_rust_swat_interchange()
        if rust_mod is None:
            raise RuntimeError(f"swat_interchange module unavailable: {rust_err}")

        interchange_dir = _join(run_dir, "interchange")
        manifest_path = _join(run_dir, "files_out.out")
        if not _exists(manifest_path):
            source_manifest = _join(self.swat_txtinout_dir, "files_out.out")
            latest_run = self._resolve_latest_run_dir(None)
            is_latest = latest_run is None or os.path.abspath(latest_run) == run_dir
            if self.swat_interchange_delete_manifest:
                self.logger.debug(
                    "SWAT interchange: manifest fallback disabled because delete_manifest is set"
                )
            elif not is_latest and _exists(source_manifest):
                self.logger.warning(
                    "SWAT interchange: skipping manifest fallback for historical run %s",
                    run_dir,
                )
            elif _exists(source_manifest):
                try:
                    shutil.copy2(source_manifest, manifest_path)
                except OSError as exc:
                    self.logger.warning(
                        "SWAT interchange: unable to copy files_out.out into %s: %s",
                        run_dir,
                        exc,
                    )
        include = self.swat_interchange_include or None
        exclude = self.swat_interchange_exclude or None

        if status_channel is None:
            status_channel = self._status_channel

        with self.locked():
            self.swat_interchange_status = "running"
            self.swat_interchange_summary = None
            self.last_swat_interchange_at = datetime.utcnow().isoformat()

        if status_channel:
            StatusMessenger.publish(status_channel, "SWAT interchange: starting")

        try:
            summary = rust_mod.swat_outputs_to_parquet(
                run_dir,
                interchange_dir=interchange_dir,
                manifest_path=manifest_path if _exists(manifest_path) else None,
                ncpu=self.swat_interchange_ncpu,
                chunk_rows=self.swat_interchange_chunk_rows,
                delete_after_interchange=self.swat_interchange_delete_after_interchange,
                dry_run=self.swat_interchange_dry_run,
                delete_manifest=self.swat_interchange_delete_manifest,
                fail_fast=self.swat_interchange_fail_fast,
                include=include,
                exclude=exclude,
                write_manifest=self.swat_interchange_write_manifest,
                compression=self.swat_interchange_compression,
                stale_after_hours=self.swat_interchange_stale_after_hours,
                overwrite=self.swat_interchange_overwrite,
            )
        except Exception:
            status = self._resolve_interchange_status(interchange_dir, None)
            with self.locked():
                self.swat_interchange_status = status
                self.swat_interchange_summary = None
            if status_channel:
                StatusMessenger.publish(
                    status_channel, f"SWAT interchange: {self.swat_interchange_status}"
                )
            raise

        status = self._resolve_interchange_status(interchange_dir, summary)
        with self.locked():
            self.swat_interchange_summary = summary
            self.swat_interchange_status = status

        if status_channel:
            StatusMessenger.publish(
                status_channel, f"SWAT interchange: {self.swat_interchange_status}"
            )

        try:
            from wepppy.query_engine.activate import update_catalog_entry

            update_catalog_entry(self.wd, interchange_dir)
        except Exception:
            self.logger.warning(
                "SWAT interchange: query-engine catalog update failed for %s",
                interchange_dir,
                exc_info=True,
            )

        return summary

    def _resolve_interchange_status(
        self,
        interchange_dir: str,
        summary: Optional[Dict[str, Any]],
    ) -> str:
        version_path = _join(interchange_dir, "interchange_version.json")
        if _exists(version_path):
            try:
                with open(version_path) as handle:
                    version = json.load(handle)
                status = version.get("status")
                if isinstance(status, str) and status:
                    return status
            except Exception:
                self.logger.warning(
                    "SWAT interchange: unable to read interchange_version.json at %s",
                    version_path,
                    exc_info=True,
                )

        if summary is None:
            return "error"

        error_reasons = {
            "header_error",
            "parse_error",
            "column_mismatch",
            "decode_error",
            "file_changed",
        }
        skipped = summary.get("skipped") if isinstance(summary, dict) else None
        if skipped:
            for entry in skipped:
                if not isinstance(entry, dict):
                    continue
                if entry.get("reason") in error_reasons:
                    return "partial"
        return "complete"

    def validate(
        self,
        recall_manifest: List[Dict[str, Any]],
        channels: List[Dict[str, Any]],
    ) -> None:
        if not recall_manifest:
            raise SwatNoDbLockedException("No recall files were generated.")
        if not channels:
            raise SwatNoDbLockedException("No channels were generated for SWAT connectivity.")

        recall_path = _join(self.swat_txtinout_dir, "recall.rec")
        recall_con = _join(self.swat_txtinout_dir, "recall.con")
        chandeg_con = _join(self.swat_txtinout_dir, "chandeg.con")

        if not _exists(recall_path):
            raise FileNotFoundError(f"Missing recall.rec: {recall_path}")
        if not _exists(recall_con):
            raise FileNotFoundError(f"Missing recall.con: {recall_con}")
        if not _exists(chandeg_con):
            raise FileNotFoundError(f"Missing chandeg.con: {chandeg_con}")

    def _ensure_print_prt_template_sync(self) -> None:
        if self.print_prt_template_dir == self.template_dir and self.print_prt is not None:
            return

        template_cfg = self._load_print_prt_template()
        if template_cfg is None:
            return

        if self.print_prt is not None:
            self._merge_print_prt_objects(template_cfg, self.print_prt)

        self.print_prt = template_cfg
        self.print_prt_template_dir = self.template_dir
        if not getattr(self, "print_prt_defaults_applied", False):
            self._apply_print_prt_defaults(self.print_prt)
            self.print_prt_defaults_applied = True

    def _merge_print_prt_objects(self, target: PrintPrtConfig, source: PrintPrtConfig) -> None:
        source_masks = source.objects.__dict__
        for object_name in target.object_order:
            attr_name = object_name.replace("-", "_")
            if attr_name not in source_masks:
                continue
            target.objects.set_mask(object_name, int(source_masks[attr_name]))

    def _load_print_prt_template(self) -> Optional[PrintPrtConfig]:
        template_path = _join(self.template_dir, "print.prt")
        if not _exists(template_path):
            self.logger.warning(
                "SWAT build: template print.prt missing at %s; using defaults",
                template_path,
            )
            return None
        try:
            return load_print_prt(template_path)
        except Exception as exc:
            self.logger.warning(
                "SWAT build: failed to parse template print.prt (%s); using defaults",
                exc,
            )
            return None

    def _apply_print_prt_defaults(self, print_prt: PrintPrtConfig) -> None:
        if print_prt is None:
            return
        for object_name in ("basin_wb", "channel_sd", "hyd"):
            attr_name = object_name.replace("-", "_")
            if not hasattr(print_prt.objects, attr_name):
                continue
            current = int(getattr(print_prt.objects, attr_name))
            print_prt.objects.set_mask(object_name, current | PRINT_PRT_DAILY)

        if hasattr(print_prt.objects, "recall"):
            print_prt.objects.set_mask("recall", 0)

    def _write_print_prt(self) -> None:
        if self.print_prt is None:
            return
        print_path = _join(self.swat_txtinout_dir, "print.prt")
        with open(print_path, "w") as handle:
            handle.write(self.print_prt.render())

    def _prepare_txtinout(self) -> None:
        if not _exists(self.template_dir):
            raise FileNotFoundError(f"Missing SWAT template directory: {self.template_dir}")
        if _exists(self.swat_txtinout_dir):
            shutil.rmtree(self.swat_txtinout_dir)
        shutil.copytree(self.template_dir, self.swat_txtinout_dir)
        recall_dirs = set()
        if self.recall_subdir:
            recall_dirs.add(self.recall_subdir)
        recall_dirs.add("recall")
        for dir_name in recall_dirs:
            if not dir_name:
                continue
            candidate = _join(self.swat_txtinout_dir, dir_name)
            if _exists(candidate):
                shutil.rmtree(candidate)
        self._ensure_om_water_init()
        self._ensure_plant_ini()
        self._patch_hru_surf_storage()

    def _ensure_om_water_init(self) -> None:
        om_path = _join(self.swat_txtinout_dir, "om_water.ini")
        if _exists(om_path):
            return
        header = (
            "name flo sed orgn sedp no3 solp chla nh3 no2 cbod dox "
            "san sil cla sag lag grv temp"
        )
        zeros = "0 " * 17 + "0"
        content = "\n".join(
            [
                "om_water.ini: generated by WEPPpy",
                header,
                f"no_init {zeros}",
                "",
            ]
        )
        with open(om_path, "w") as handle:
            handle.write(content)

    def _ensure_plant_ini(self) -> None:
        plant_path = _join(self.swat_txtinout_dir, "plant.ini")
        communities = self._read_landuse_communities()
        if not communities:
            return

        plant_names = self._read_plant_names()
        if not plant_names:
            return

        if not _exists(plant_path):
            self._write_plant_ini(plant_path, communities, plant_names)
            return

        existing = self._read_plant_ini_communities(plant_path)
        missing = [comm for comm in communities if comm not in existing]
        if missing:
            self._append_plant_ini(plant_path, missing, plant_names)

    def _read_landuse_communities(self) -> List[str]:
        landuse_path = _join(self.swat_txtinout_dir, "landuse.lum")
        if not _exists(landuse_path):
            return []
        with open(landuse_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return []
        header = lines[1].split()
        col_idx = None
        for idx, name in enumerate(header):
            if name.lower() in ("plnt_com", "plant_com", "plant_comm", "plant_community"):
                col_idx = idx
                break
        if col_idx is None:
            return []
        communities: List[str] = []
        for line in lines[2:]:
            parts = line.split()
            if len(parts) <= col_idx:
                continue
            name = parts[col_idx]
            if not name or name.lower() == "null":
                continue
            if name not in communities:
                communities.append(name)
        return communities

    def _read_plant_names(self) -> List[str]:
        plants_path = _join(self.swat_txtinout_dir, "plants.plt")
        if not _exists(plants_path):
            return []
        with open(plants_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return []
        names: List[str] = []
        for line in lines[2:]:
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            if name not in names:
                names.append(name)
        return names

    def _read_plant_ini_communities(self, plant_path: str) -> List[str]:
        with open(plant_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return []
        communities: List[str] = []
        idx = 2
        while idx < len(lines):
            parts = lines[idx].split()
            if len(parts) < 2:
                idx += 1
                continue
            name = parts[0]
            try:
                count = int(float(parts[1]))
            except ValueError:
                count = 0
            communities.append(name)
            idx += 1 + max(count, 0)
        return communities

    def _choose_plant_for_community(self, community: str, plant_names: List[str]) -> str:
        plant_set = {name.lower(): name for name in plant_names}
        comm = community.lower()
        base = comm
        if comm.endswith("_comm"):
            base = comm[:-5]
        if base in plant_set:
            return plant_set[base]
        if "rye" in comm and "rye" in plant_set:
            return plant_set["rye"]
        if "rice" in comm:
            if "rice140" in plant_set and "140" in comm:
                return plant_set["rice140"]
            if "rice" in plant_set:
                return plant_set["rice"]
        for prefix in ("frst", "frse", "gras", "wetn", "wetw", "orcd", "agrl"):
            if prefix in comm and prefix in plant_set:
                return plant_set[prefix]
        if "agrl" in plant_set:
            return plant_set["agrl"]
        return plant_names[0]

    def _write_plant_ini(
        self,
        plant_path: str,
        communities: List[str],
        plant_names: List[str],
    ) -> None:
        header = (
            "pcom_name plt_cnt rot_yr_ini plt_name lc_status "
            "lai_init bm_init phu_init plnt_pop yrs_init rsd_init"
        )
        lines = ["plant.ini: generated by WEPPpy", header]
        for comm in communities:
            plant = self._choose_plant_for_community(comm, plant_names)
            lines.append(f"{comm} 1 1")
            lines.append(
                f"{plant} n 0.00000 0.00000 0.00000 10000.00000 0.00000 0.00000"
            )
        with open(plant_path, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    def _append_plant_ini(
        self,
        plant_path: str,
        communities: List[str],
        plant_names: List[str],
    ) -> None:
        lines = []
        for comm in communities:
            plant = self._choose_plant_for_community(comm, plant_names)
            lines.append(f"{comm} 1 1")
            lines.append(
                f"{plant} n 0.00000 0.00000 0.00000 10000.00000 0.00000 0.00000"
            )
        with open(plant_path, "a") as handle:
            handle.write("\n".join(lines) + "\n")

    def _patch_hru_surf_storage(self) -> None:
        hru_path = _join(self.swat_txtinout_dir, "hru-data.hru")
        if not _exists(hru_path):
            return
        with open(hru_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return
        header = lines[1].split()
        surf_idx = None
        for idx, name in enumerate(header):
            if name.lower() in ("surf_stor", "surfstor", "surf_store"):
                surf_idx = idx
                break
        if surf_idx is None:
            return
        updated = False
        for idx in range(2, len(lines)):
            parts = lines[idx].split()
            if len(parts) <= surf_idx:
                continue
            if parts[surf_idx].lower() != "null":
                parts[surf_idx] = "null"
                lines[idx] = " ".join(parts)
                updated = True
        if updated:
            with open(hru_path, "w") as handle:
                handle.write("\n".join(lines) + "\n")

    def _normalize_climate_nbyr(self) -> None:
        cli_files = ("pcp.cli", "tmp.cli", "slr.cli", "wnd.cli", "hmd.cli", "pet.cli")
        for cli_name in cli_files:
            cli_path = _join(self.swat_txtinout_dir, cli_name)
            if not _exists(cli_path):
                continue
            for filename in self._read_cli_filenames(cli_path):
                data_path = _join(self.swat_txtinout_dir, filename)
                if not _exists(data_path):
                    continue
                if self._patch_cli_nbyr(data_path):
                    self.logger.info("SWAT build: updated nbyr in %s", data_path)

    def _validate_recall_wst(self) -> None:
        stations = self._load_weather_station_names()
        if not stations:
            raise FileNotFoundError(
                f"Missing or empty weather-sta.cli in {self.swat_txtinout_dir}"
            )
        recall_wst = (self.recall_wst or "").strip()
        if recall_wst.lower() == "auto" or not recall_wst:
            self.recall_wst = stations[0]
            self.logger.info(
                "SWAT build: recall_wst auto-selected '%s' from weather-sta.cli",
                self.recall_wst,
            )
            return
        if recall_wst not in stations:
            if recall_wst.lower() == "wea1":
                self.recall_wst = stations[0]
                self.logger.warning(
                    "SWAT build: recall_wst 'wea1' not found; defaulting to '%s'. "
                    "Set recall_wst=auto or an explicit station to avoid this warning.",
                    self.recall_wst,
                )
                return
            raise SwatNoDbLockedException(
                f"recall_wst '{self.recall_wst}' not found in weather-sta.cli; available: {', '.join(stations)}"
            )

    def _load_weather_station_names(self) -> List[str]:
        cli_path = _join(self.swat_txtinout_dir, "weather-sta.cli")
        if not _exists(cli_path):
            return []
        with open(cli_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return []
        stations: List[str] = []
        for line in lines[2:]:
            parts = line.split()
            if not parts:
                continue
            stations.append(parts[0])
        return stations

    def _read_cli_filenames(self, cli_path: str) -> List[str]:
        with open(cli_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return []
        filenames: List[str] = []
        for line in lines[2:]:
            parts = line.split()
            if not parts:
                continue
            filenames.append(parts[0])
        return filenames

    def _patch_cli_nbyr(self, data_path: str) -> bool:
        with open(data_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 4:
            return False
        values = lines[2].split()
        if not values:
            return False
        try:
            nbyr = int(float(values[0]))
        except ValueError:
            return False

        count = 0
        last_year: Optional[str] = None
        for line in lines[3:]:
            parts = line.split()
            if not parts:
                continue
            year = parts[0]
            if year != last_year:
                count += 1
                last_year = year
        if count == 0 or count == nbyr:
            return False
        values[0] = str(count)
        lines[2] = " ".join(values)
        with open(data_path, "w") as handle:
            handle.write("\n".join(lines) + "\n")
        return True

    def _normalize_recall_paths(self) -> None:
        recall_path = _join(self.swat_txtinout_dir, "recall.rec")
        if not _exists(recall_path):
            return
        with open(recall_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return
        header = lines[1].split()
        fname_idx = None
        for idx, name in enumerate(header):
            if name.lower() in ("filename", "fname"):
                fname_idx = idx
                break
        if fname_idx is None:
            fname_idx = 3

        updated = False
        for idx in range(2, len(lines)):
            parts = lines[idx].split()
            if len(parts) <= fname_idx:
                continue
            raw = parts[fname_idx]
            if not raw:
                continue
            normalized = raw.replace("\\", "/").lstrip("./")
            basename = os.path.basename(normalized)
            dest = _join(self.swat_txtinout_dir, basename)
            if not _exists(dest):
                src = None
                if normalized:
                    candidate = normalized
                    if os.path.isabs(candidate):
                        src = candidate if _exists(candidate) else None
                    else:
                        candidate = _join(self.swat_txtinout_dir, candidate)
                        if _exists(candidate):
                            src = candidate
                if src is None and self.recall_subdir:
                    candidate = _join(self.swat_txtinout_dir, self.recall_subdir, basename)
                    if _exists(candidate):
                        src = candidate
                if src is not None:
                    shutil.copy2(src, dest)

            if basename != raw:
                parts[fname_idx] = basename
                lines[idx] = " ".join(parts)
                updated = True

        if updated:
            with open(recall_path, "w") as handle:
                handle.write("\n".join(lines) + "\n")

    def _patch_recall_con_areas(self) -> None:
        recall_con = _join(self.swat_txtinout_dir, "recall.con")
        if not _exists(recall_con):
            return

        areas = self._load_hillslope_areas()
        if not areas:
            return

        with open(recall_con) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return

        header = lines[1].split()
        area_idx = None
        gis_idx = None
        for idx, name in enumerate(header):
            lower = name.lower()
            if lower in ("area_ha", "area"):
                area_idx = idx
            if lower in ("gis_id", "gisid"):
                gis_idx = idx
        if area_idx is None or gis_idx is None:
            return

        updated = False
        for idx in range(2, len(lines)):
            parts = lines[idx].split()
            if len(parts) <= max(area_idx, gis_idx):
                continue
            try:
                wepp_id = int(float(parts[gis_idx]))
            except ValueError:
                continue
            area_ha = areas.get(wepp_id)
            if area_ha is None:
                continue
            parts[area_idx] = f"{area_ha:.3f}"
            lines[idx] = " ".join(parts)
            updated = True

        if updated:
            with open(recall_con, "w") as handle:
                handle.write("\n".join(lines) + "\n")

    def _load_hillslope_areas(self) -> Dict[int, float]:
        hillslopes_parquet = _join(self.wd, "watershed", "hillslopes.parquet")
        if not _exists(hillslopes_parquet):
            return {}
        with duckdb.connect() as con:
            cols = _read_parquet_columns(con, hillslopes_parquet)
            wepp_col = _resolve_column(cols, ("wepp_id", "WeppID"), hillslopes_parquet)
            area_col = _resolve_column_optional(cols, ("area", "area_m2", "area_m", "area_sq_m"))
            if area_col is None:
                return {}
            rows = con.execute(
                "SELECT {wepp}, {area} FROM read_parquet('{path}')".format(
                    wepp=_quote_ident(wepp_col),
                    area=_quote_ident(area_col),
                    path=_escape_sql_path(hillslopes_parquet),
                )
            ).fetchall()
        areas: Dict[int, float] = {}
        for wepp_id, area_m2 in rows:
            if wepp_id is None or area_m2 is None:
                continue
            try:
                area_val = float(area_m2)
            except (TypeError, ValueError):
                continue
            if area_val <= 0.0:
                continue
            areas[int(wepp_id)] = area_val / 10_000.0
        return areas

    def _get_recall_calendar_lookup(self) -> CalendarLookup:
        if self._recall_calendar_ready:
            return self._recall_calendar_lookup or {}

        self._recall_calendar_ready = True
        wepp_output_dir = Path(self.wd) / "wepp" / "output"
        if not wepp_output_dir.exists():
            self._recall_calendar_lookup = {}
            return self._recall_calendar_lookup

        climate_files = None
        if self.cli_calendar_path:
            climate_files = [os.path.basename(self.cli_calendar_path)]
        self._recall_calendar_lookup = _build_cli_calendar_lookup(
            wepp_output_dir,
            climate_files=climate_files,
            log=self.logger,
        )
        return self._recall_calendar_lookup or {}

    def _convert_wepp_recall_files(self) -> None:
        recall_path = _join(self.swat_txtinout_dir, "recall.rec")
        if not _exists(recall_path):
            return
        with open(recall_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return

        header = lines[1].split()
        name_idx = 1 if len(header) > 1 else None
        fname_idx = None
        for idx, name in enumerate(header):
            if name.lower() in ("filename", "fname"):
                fname_idx = idx
                break
        if fname_idx is None:
            fname_idx = 3

        for line in lines[2:]:
            parts = line.split()
            if len(parts) <= fname_idx:
                continue
            recall_name = parts[name_idx] if name_idx is not None and len(parts) > name_idx else ""
            filename = parts[fname_idx]
            data_path = _join(self.swat_txtinout_dir, filename)
            if not _exists(data_path):
                continue
            self._convert_wepp_recall_file(data_path, recall_name)

    def _convert_wepp_recall_file(self, data_path: str, recall_name: str) -> None:
        with open(data_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 4:
            return

        header_tokens = lines[2].split()
        if "IYR" not in header_tokens or "ISTEP" not in header_tokens:
            return

        index = {name: idx for idx, name in enumerate(header_tokens)}
        required = [
            "IYR",
            "ISTEP",
            "flo",
            "sed",
            "orgn",
            "sedp",
            "no3",
            "solp",
            "chla",
            "nh3",
            "no2",
            "cbod",
            "dox",
            "san",
            "sil",
            "cla",
            "sag",
            "lag",
            "grv",
            "temp",
        ]
        for key in required:
            if key not in index:
                return

        calendar_lookup = self._get_recall_calendar_lookup()
        warned_calendar = False
        warned_bounds = False

        def _year_length(year: int) -> int:
            if year < 1:
                return 365
            try:
                return (datetime(year + 1, 1, 1) - datetime(year, 1, 1)).days
            except ValueError:
                return 365

        def _normalize_jday(year: int, jday: int) -> tuple[int, int, int]:
            nonlocal warned_calendar
            nonlocal warned_bounds

            if calendar_lookup and year in calendar_lookup:
                days = calendar_lookup.get(year, [])
                if days:
                    max_day = len(days)
                    if jday < 1 or jday > max_day:
                        if not warned_calendar:
                            self.logger.warning(
                                "SWAT recall: Julian day %s outside CLI calendar for year %s; "
                                "clamping to 1..%s",
                                jday,
                                year,
                                max_day,
                            )
                            warned_calendar = True
                        jday = max(1, min(jday, max_day))
                    month, day = days[jday - 1]
                    return jday, int(month), int(day)

            max_day = _year_length(year)
            if jday < 1 or jday > max_day:
                if not warned_bounds:
                    self.logger.warning(
                        "SWAT recall: Julian day %s outside year length %s for year %s; "
                        "clamping to bounds",
                        jday,
                        max_day,
                        year,
                    )
                    warned_bounds = True
                jday = max(1, min(jday, max_day))

            calendar_year = year if year >= 1 else 2001
            month, day = _julian_to_calendar(calendar_year, jday, calendar_lookup=None)
            return jday, month, day

        data_rows: List[str] = []
        years: List[int] = []
        ob_typ = self.recall_object_type
        ob_name = recall_name or os.path.splitext(os.path.basename(data_path))[0]
        for line in lines[3:]:
            parts = line.split()
            if not parts:
                continue
            try:
                iyr = int(float(parts[index["IYR"]]))
                istep = int(float(parts[index["ISTEP"]]))
            except (ValueError, IndexError):
                continue
            jday, mo, day_mo = _normalize_jday(iyr, istep)
            years.append(iyr)
            values = []
            for key in required[2:]:
                try:
                    values.append(float(parts[index[key]]))
                except (ValueError, IndexError):
                    values.append(0.0)
            formatted = " ".join(f"{val:.6f}" for val in values)
            data_rows.append(
                f"{jday} {mo} {day_mo} {iyr} {ob_typ} {ob_name} {formatted}"
            )

        if not data_rows:
            return

        nbyr = None
        try:
            nbyr = int(float(lines[1].split()[0]))
        except (ValueError, IndexError):
            pass
        if not nbyr and years:
            nbyr = len(sorted(set(years)))
        if not nbyr:
            nbyr = 1

        header = (
            "jday mo day_mo iyr ob_typ ob_name flo sed orgn sedp no3 solp chla nh3 "
            "no2 cbod dox san sil cla sag lag grv temp"
        )
        output = [lines[0], str(nbyr), header]
        output.extend(data_rows)
        with open(data_path, "w") as handle:
            handle.write("\n".join(output) + "\n")

    def _align_recall_years(self) -> None:
        recall_paths = self._read_recall_paths()
        if not recall_paths:
            return

        target_year = self._resolve_recall_start_year()
        if target_year is None:
            return

        updated = 0
        for path in recall_paths:
            if self._shift_recall_years(path, target_year):
                updated += 1

        if updated:
            self.logger.info(
                "SWAT build: shifted recall years to start at %s for %s file(s)",
                target_year,
                updated,
            )

    def _read_recall_paths(self) -> List[str]:
        recall_path = _join(self.swat_txtinout_dir, "recall.rec")
        if not _exists(recall_path):
            return []

        with open(recall_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return []

        header = lines[1].split()
        fname_idx = None
        for idx, name in enumerate(header):
            if name.lower() in ("filename", "fname"):
                fname_idx = idx
                break
        if fname_idx is None:
            fname_idx = 3

        recall_paths: List[str] = []
        for line in lines[2:]:
            parts = line.split()
            if len(parts) <= fname_idx:
                continue
            filename = parts[fname_idx].replace("\\", "/")
            candidate = _join(self.swat_txtinout_dir, filename)
            if not _exists(candidate) and self.recall_subdir:
                candidate = _join(self.swat_txtinout_dir, self.recall_subdir, os.path.basename(filename))
            if _exists(candidate):
                recall_paths.append(candidate)

        return recall_paths

    def _resolve_recall_start_year(self) -> Optional[int]:
        wepp_start = self._read_wepp_cli_start_year()
        if wepp_start is not None and wepp_start > 1:
            override = None
            if self._configparser.has_option("swat", "time_start_year"):
                override = self.config_get_int("swat", "time_start_year", None)
                if override is not None and override < 1:
                    raise SwatNoDbLockedException(
                        f"time_start_year must be >= 1; got {override}"
                    )
                if override is not None and override > 1 and override != wepp_start:
                    self.logger.warning(
                        "SWAT build: time_start_year %s ignored; using WEPP climate start year %s",
                        override,
                        wepp_start,
                    )
            if self.force_time_start_year and override is not None and override != wepp_start:
                self.logger.warning(
                    "SWAT build: force_time_start_year ignored; using WEPP climate start year %s",
                    wepp_start,
                )
            return wepp_start

        if self._configparser.has_option("swat", "time_start_year"):
            override = self.config_get_int("swat", "time_start_year", None)
            if override is None:
                return None
            if override < 1:
                raise SwatNoDbLockedException(
                    f"time_start_year must be >= 1; got {override}"
                )
            if override > 1 or self.force_time_start_year:
                return override

        time_start = self._read_time_sim_start_year()
        if time_start is not None and time_start > 1:
            return time_start

        climate_start = self._read_swat_pcp_start_year()
        if climate_start is not None and climate_start > 1:
            return climate_start

        return None

    def _read_time_sim_start_year(self) -> Optional[int]:
        time_path = _join(self.swat_txtinout_dir, "time.sim")
        if not _exists(time_path):
            return None

        with open(time_path) as handle:
            lines = handle.read().splitlines()

        for line in lines:
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                int(float(parts[0]))
                year_start = int(float(parts[1]))
            except ValueError:
                continue
            return year_start
        return None

    def _read_wepp_cli_start_year(self) -> Optional[int]:
        cli_path = self._find_wepp_cli_path()
        if cli_path is None or not _exists(cli_path):
            return None

        with open(cli_path) as handle:
            lines = handle.read().splitlines()

        header_idx = None
        for idx, line in enumerate(lines):
            tokens = line.strip().lower().split()
            if not tokens:
                continue
            if tokens[0] in ("da", "day") and ("year" in tokens or "yr" in tokens):
                header_idx = idx
                break

        if header_idx is None:
            return None

        for line in lines[header_idx + 1 :]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("("):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            try:
                return int(float(parts[2]))
            except ValueError:
                continue
        return None

    def _find_wepp_cli_path(self) -> Optional[str]:
        base = Path(self.wd)
        for candidate in (base, *base.parents):
            climate_dir = candidate / "climate"
            if not climate_dir.exists():
                continue
            wepp_cli = climate_dir / "wepp.cli"
            if wepp_cli.exists():
                return str(wepp_cli)
            cli_candidates = sorted(climate_dir.glob("*.cli"))
            if cli_candidates:
                return str(cli_candidates[0])
        return None

    def _read_swat_pcp_start_year(self) -> Optional[int]:
        cli_path = _join(self.swat_txtinout_dir, "pcp.cli")
        if not _exists(cli_path):
            return None

        filenames = self._read_cli_filenames(cli_path)
        if not filenames:
            return None

        data_path = _join(self.swat_txtinout_dir, filenames[0])
        if not _exists(data_path):
            return None

        with open(data_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 4:
            return None

        for line in lines[3:]:
            parts = line.split()
            if not parts:
                continue
            try:
                return int(float(parts[0]))
            except ValueError:
                continue
        return None

    def _shift_recall_years(self, data_path: str, target_start_year: int) -> bool:
        with open(data_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 4:
            return False

        header = lines[2].split()
        year_idx = None
        for idx, name in enumerate(header):
            if name.lower() in ("iyr", "year"):
                year_idx = idx
                break
        if year_idx is None:
            return False

        first_year: Optional[int] = None
        for line in lines[3:]:
            parts = line.split()
            if len(parts) <= year_idx:
                continue
            try:
                first_year = int(float(parts[year_idx]))
                break
            except ValueError:
                continue

        if first_year is None:
            return False

        offset = target_start_year - first_year
        if offset == 0:
            return False

        updated = False
        for idx in range(3, len(lines)):
            parts = lines[idx].split()
            if len(parts) <= year_idx:
                continue
            try:
                year = int(float(parts[year_idx]))
            except ValueError:
                continue
            parts[year_idx] = str(year + offset)
            lines[idx] = " ".join(parts)
            updated = True

        if updated:
            with open(data_path, "w") as handle:
                handle.write("\n".join(lines) + "\n")
        return updated

    def _append_log(self, log_path: str, message: str) -> None:
        timestamp = datetime.utcnow().isoformat()
        with open(log_path, "a") as handle:
            handle.write(f"{timestamp} {message}\n")

    def _estimate_total_area_ha(self) -> Optional[float]:
        hillslopes_parquet = _join(self.wd, 'watershed', 'hillslopes.parquet')
        if not _exists(hillslopes_parquet):
            return None
        with duckdb.connect() as con:
            cols = _read_parquet_columns(con, hillslopes_parquet)
            area_col = _resolve_column_optional(cols, ('area', 'area_m2', 'area_m', 'area_sq_m'))
            if area_col is None:
                return None
            total = con.execute(
                f"SELECT SUM({area_col}) FROM read_parquet('{_escape_sql_path(hillslopes_parquet)}')"
            ).fetchone()[0]
        if total is None:
            return None
        return float(total) / 10_000.0

    def _patch_object_counts(
        self,
        channel_count: int,
        recall_count: int,
        total_area_ha: Optional[float],
    ) -> None:
        object_path = _join(self.swat_txtinout_dir, "object.cnt")
        if not _exists(object_path):
            return
        with open(object_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return

        header_line = lines[1]
        header = header_line.split()
        values = lines[2].split()
        if len(values) < len(header):
            values.extend(["0"] * (len(header) - len(values)))
        elif len(values) > len(header):
            values = values[:len(header)]

        col_index = {name: idx for idx, name in enumerate(header)}
        if "lcha" in col_index:
            values[col_index["lcha"]] = str(channel_count)
        if "cha" in col_index:
            if self.recall_object_type == "sdc":
                values[col_index["cha"]] = "0"
            else:
                values[col_index["cha"]] = str(channel_count)
        if "rec" in col_index:
            values[col_index["rec"]] = str(recall_count)
        if self.disable_aquifer:
            for key in ("aqu", "aqu2d"):
                if key in col_index:
                    values[col_index[key]] = "0"
        if total_area_ha is not None:
            for key in ("ls_area", "tot_area"):
                if key in col_index:
                    values[col_index[key]] = f"{total_area_ha:.4f}"
        if "obj" in col_index:
            total = 0
            for key in header:
                if key in ("name", "ls_area", "tot_area", "obj"):
                    continue
                try:
                    total += int(float(values[col_index[key]]))
                except (KeyError, ValueError):
                    continue
            values[col_index["obj"]] = str(total)

        lines[2] = " ".join(values)
        with open(object_path, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    def _patch_rout_unit_con(self) -> None:
        rout_path = _join(self.swat_txtinout_dir, "rout_unit.con")
        if not _exists(rout_path):
            return
        with open(rout_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return

        header = lines[1].split()
        if "out_tot" not in header:
            return
        out_tot_idx = header.index("out_tot")
        prefix_len = out_tot_idx + 1

        updated = False
        new_lines = [lines[0], lines[1]]
        for line in lines[2:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) <= prefix_len:
                new_lines.append(line)
                continue
            head = parts[:prefix_len]
            tail = parts[prefix_len:]
            groups = [
                tail[i : i + 4]
                for i in range(0, len(tail), 4)
                if i + 3 < len(tail)
            ]
            filtered = [group for group in groups if group[0].lower() != "aqu"]
            if len(filtered) != len(groups):
                updated = True
            head[out_tot_idx] = str(len(filtered))
            flat = [item for group in filtered for item in group]
            new_lines.append(" ".join(head + flat))

        if updated:
            with open(rout_path, "w") as handle:
                handle.write("\n".join(new_lines) + "\n")

    def _count_written_recall(self, recall_manifest: List[Dict[str, Any]]) -> int:
        return sum(1 for entry in recall_manifest if entry.get("status") == "written")

    def _patch_time_sim(
        self,
        recall_manifest: List[Dict[str, Any]],
    ) -> Optional[Tuple[int, int, int, int]]:
        if not recall_manifest:
            return None

        date_bounds = self._read_recall_bounds(recall_manifest)
        if date_bounds is None:
            return None

        year_start, day_start, year_end, day_end = date_bounds
        time_path = _join(self.swat_txtinout_dir, "time.sim")
        if not _exists(time_path):
            return None

        with open(time_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return None

        step = "0"
        current = lines[2].split()
        if len(current) >= 5:
            step = current[4]

        lines[2] = f"{day_start:>8} {year_start:>10} {day_end:>10} {year_end:>10} {step:>10}"

        with open(time_path, "w") as handle:
            handle.write("\n".join(lines) + "\n")

        return (year_start, day_start, year_end, day_end)

    def _read_recall_bounds(
        self,
        recall_manifest: List[Dict[str, Any]],
    ) -> Optional[Tuple[int, int, int, int]]:
        recall_paths = self._read_recall_paths()
        if not recall_paths:
            for entry in recall_manifest:
                if entry.get("status") != "written":
                    continue
                recall_file = entry.get("recall_file")
                if not recall_file:
                    continue
                if _exists(recall_file):
                    recall_paths.append(recall_file)
                else:
                    recall_paths.append(
                        _join(self.swat_txtinout_dir, os.path.basename(recall_file))
                    )

        if not recall_paths:
            return None

        bounds: Optional[Tuple[int, int, int, int]] = None
        for recall_file in recall_paths:
            if not _exists(recall_file):
                continue
            file_bounds = self._read_recall_file_bounds(recall_file)
            if file_bounds is None:
                continue
            if bounds is None:
                bounds = file_bounds
                continue
            start = min((bounds[0], bounds[1]), (file_bounds[0], file_bounds[1]))
            end = max((bounds[2], bounds[3]), (file_bounds[2], file_bounds[3]))
            bounds = (start[0], start[1], end[0], end[1])

        return bounds

    def _read_recall_file_bounds(self, recall_file: str) -> Optional[Tuple[int, int, int, int]]:
        with open(recall_file) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 4:
            return None

        header_line = lines[2].strip()
        if not header_line:
            for candidate in lines[3:]:
                if candidate.strip():
                    header_line = candidate.strip()
                    break
        if not header_line:
            return None

        header = [token.lower() for token in header_line.split()]
        if "iyr" not in header:
            return None
        year_idx = header.index("iyr")
        if "jday" in header:
            day_idx = header.index("jday")
        elif "istep" in header:
            day_idx = header.index("istep")
        else:
            day_idx = 1

        first: Optional[Tuple[int, int]] = None
        last: Optional[Tuple[int, int]] = None
        for line in lines[3:]:
            parts = line.split()
            if len(parts) <= max(year_idx, day_idx):
                continue
            try:
                year = int(float(parts[year_idx]))
                day = int(float(parts[day_idx]))
            except ValueError:
                continue
            if first is None:
                first = (year, day)
            last = (year, day)

        if first is None or last is None:
            return None

        return first[0], first[1], last[0], last[1]

    def _load_channels(self) -> List[Dict[str, Any]]:
        channels_parquet = _join(self.wd, 'watershed', 'channels.parquet')
        if not _exists(channels_parquet):
            raise FileNotFoundError(f"Missing channels parquet: {channels_parquet}")

        with duckdb.connect() as con:
            cols = _read_parquet_columns(con, channels_parquet)
            topaz_col = _resolve_column(cols, ('topaz_id', 'TopazID'), channels_parquet)
            chn_enum_col = _resolve_column(cols, ('chn_enum', 'ChnEnum'), channels_parquet)

            length_col = _resolve_column_optional(cols, ('length', 'len', 'length_m', 'len_m'))
            slope_col = _resolve_column_optional(cols, ('slope_scalar', 'slope', 'slp'))
            width_col = _resolve_column_optional(cols, ('width', 'width_m', 'chn_width'))
            order_col = _resolve_column_optional(cols, ('order', 'chn_order', 'stream_order', 'strm_order'))
            area_col = _resolve_column_optional(cols, ('area', 'area_m2', 'area_m', 'area_sq_m'))
            lat_col = _resolve_column_optional(cols, ('centroid_lat', 'centroid_latitude', 'lat'))
            lon_col = _resolve_column_optional(cols, ('centroid_lon', 'centroid_lng', 'centroid_longitude', 'lon', 'lng'))
            elev_col = _resolve_column_optional(cols, ('elevation', 'elev', 'elev_m'))

            select_cols = [
                f"{_quote_ident(topaz_col)} as topaz_id",
                f"{_quote_ident(chn_enum_col)} as chn_enum",
                _select_or_null(length_col, "length_m"),
                _select_or_null(slope_col, "slope"),
                _select_or_null(width_col, "width_m"),
                _select_or_null(order_col, "order"),
                _select_or_null(area_col, "area_m2"),
                _select_or_null(lat_col, "centroid_lat"),
                _select_or_null(lon_col, "centroid_lon"),
                _select_or_null(elev_col, "elevation"),
            ]

            rows = con.execute(
                f"SELECT {', '.join(select_cols)} FROM read_parquet('{_escape_sql_path(channels_parquet)}')"
            ).fetchall()

        netw_areas = self._load_netw_areas()
        channels: List[Dict[str, Any]] = []
        for row in rows:
            (
                topaz_id,
                chn_enum,
                length_m,
                slope,
                width_m,
                order,
                area_m2,
                centroid_lat,
                centroid_lon,
                elevation,
            ) = row

            if chn_enum is None:
                continue

            topaz_id = int(topaz_id)
            chn_enum = int(chn_enum)
            length_value = _safe_float(length_m, default=None)
            length_km = length_value / 1000.0 if length_value is not None else 1.0
            if length_km <= 0.0:
                length_km = 0.001
            slope_val = _safe_float(slope, default=0.001)
            if slope_val > 1.0:
                slope_val = slope_val / 100.0
            if slope_val <= 0.0:
                slope_val = 0.001

            area_km2 = None
            if area_m2 is not None:
                area_value = _safe_float(area_m2, default=None)
                if area_value is not None:
                    area_km2 = area_value / 1_000_000.0
            if area_km2 is None:
                area_km2 = netw_areas.get(topaz_id)
            if area_km2 is None or area_km2 <= 0.0:
                area_km2 = 1.0

            area_ha = area_km2 * 100.0

            width_value = _safe_float(width_m, default=None)
            width_method = self.width_method
            if width_method not in ("bieger2015", "qswat"):
                raise SwatNoDbLockedException(
                    f"Unsupported width_method '{self.width_method}'; use 'bieger2015' or 'qswat'."
                )
            if width_method == "qswat":
                width_value = self.qswat_wm * (area_km2 ** self.qswat_we)
            elif width_value is None:
                if self.width_fallback == "qswat":
                    self.logger.warning(
                        "SWAT build: channel width missing; falling back to QSWAT regression "
                        "(set width_fallback=error to disable)."
                    )
                    width_value = self.qswat_wm * (area_km2 ** self.qswat_we)
                else:
                    raise SwatNoDbLockedException(
                        "Channel width missing in channels.parquet with width_method=bieger2015. "
                        "Provide width data or set width_method=qswat/width_fallback=qswat."
                    )

            depth_value = self.qswat_dm * (area_km2 ** self.qswat_de)
            wd_rto = width_value / depth_value if depth_value else 1.0

            channels.append(
                {
                    "topaz_id": topaz_id,
                    "chn_enum": chn_enum,
                    "length_km": length_km,
                    "slope": slope_val,
                    "width_m": width_value,
                    "depth_m": depth_value,
                    "order": int(order) if order is not None else 1,
                    "area_ha": area_ha,
                    "centroid_lat": _safe_float(centroid_lat, default=0.0),
                    "centroid_lon": _safe_float(centroid_lon, default=0.0),
                    "elevation": _safe_float(elevation, default=0.0),
                    "wd_rto": wd_rto,
                }
            )

        channels.sort(key=lambda item: item["chn_enum"])
        return channels

    def _load_netw_areas(self) -> Dict[int, float]:
        netw_path = _join(self.wd, "dem", "wbt", "netw.tsv")
        if not _exists(netw_path):
            return {}
        with open(netw_path, newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames is None:
                return {}
            keys = {key.lower(): key for key in reader.fieldnames}
            id_key = None
            for candidate in ("link", "id", "topaz_id", "topaz", "channel", "chn_id"):
                if candidate in keys:
                    id_key = keys[candidate]
                    break
            area_key = None
            for candidate in ("areaup", "area_up", "area", "area_km2"):
                if candidate in keys:
                    area_key = keys[candidate]
                    break
            if id_key is None or area_key is None:
                return {}

            areas: Dict[int, float] = {}
            for row in reader:
                try:
                    topaz_id = int(float(row[id_key]))
                    area_val = float(row[area_key])
                except (TypeError, ValueError):
                    continue
                areas[topaz_id] = area_val

        if not areas:
            return areas

        unit_override = (self.netw_area_units or "auto").lower()
        if unit_override in ("m2", "meter2", "meters2", "sq_m", "sqm", "m^2"):
            unit = "m2"
        elif unit_override in ("km2", "sq_km", "sqkm", "km^2"):
            unit = "km2"
        elif unit_override not in ("auto", ""):
            raise SwatNoDbLockedException(
                f"Unsupported netw_area_units '{self.netw_area_units}'; use 'auto', 'm2', or 'km2'."
            )
        else:
            unit = _infer_netw_area_units(area_key, reader.fieldnames or [])

        if unit == "m2":
            areas = {key: value / 1_000_000.0 for key, value in areas.items()}
        elif unit is None:
            self.logger.warning(
                "SWAT build: netw.tsv area units ambiguous for '%s'; "
                "falling back to magnitude heuristic. Set netw_area_units to 'm2' or 'km2'.",
                area_key,
            )
            max_area = max(areas.values())
            if max_area > 10_000:
                areas = {key: value / 1_000_000.0 for key, value in areas.items()}
        return areas

    def _build_downstream_map(self, channels: List[Dict[str, Any]]) -> Dict[int, Optional[int]]:
        network_path = _join(self.wd, "watershed", "network.txt")
        downstream: Dict[int, Optional[int]] = {}
        if _exists(network_path):
            network = read_network(network_path)
            for down_topaz, upstreams in network.items():
                for upstream in upstreams:
                    if upstream == down_topaz:
                        continue
                    downstream[int(upstream)] = int(down_topaz)
        else:
            for channel in channels:
                downstream[channel["topaz_id"]] = None

        chn_lookup = {channel["topaz_id"]: channel["chn_enum"] for channel in channels}
        return {
            channel["chn_enum"]: chn_lookup.get(downstream.get(channel["topaz_id"])) for channel in channels
        }

    def _write_chandeg_con(
        self,
        channels: List[Dict[str, Any]],
        downstream_map: Dict[int, Optional[int]],
    ) -> None:
        chandeg_path = _join(self.swat_txtinout_dir, "chandeg.con")
        title = "chandeg.con: generated by WEPPpy"
        header = (
            "      id  name                gis_id          area           lat           lon          elev"
            "      lcha               wst       cst      ovfl      rule   out_tot       obj_typ    obj_id"
            "       hyd_typ          frac"
        )

        width = max(2, len(str(max(ch["chn_enum"] for ch in channels))))

        lines = [title, header]
        for channel in channels:
            chn_enum = channel["chn_enum"]
            name = f"cha{chn_enum:0{width}d}"
            gis_id = channel["topaz_id"]
            area = channel["area_ha"]
            lat = channel["centroid_lat"]
            lon = channel["centroid_lon"]
            elev = channel["elevation"]
            lcha = chn_enum
            wst = self.recall_wst
            cst = 0
            ovfl = 0
            rule = 0
            downstream = downstream_map.get(chn_enum)
            if downstream:
                out_tot = 1
                obj_typ = self.recall_object_type
                obj_id = downstream
                hyd_typ = "tot"
                frac = 1.0
                line = (
                    f"{chn_enum:>8} {name:>6} {gis_id:>12} {area:>12.5f} {lat:>12.5f} {lon:>12.5f}"
                    f" {elev:>12.3f} {lcha:>8} {wst:>18} {cst:>8} {ovfl:>8} {rule:>8} {out_tot:>8}"
                    f" {obj_typ:>10} {obj_id:>8} {hyd_typ:>10} {frac:>12.5f}"
                )
            else:
                out_tot = 0
                line = (
                    f"{chn_enum:>8} {name:>6} {gis_id:>12} {area:>12.5f} {lat:>12.5f} {lon:>12.5f}"
                    f" {elev:>12.3f} {lcha:>8} {wst:>18} {cst:>8} {ovfl:>8} {rule:>8} {out_tot:>8}"
                )
            lines.append(line)

        with open(chandeg_path, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    def _write_channel_lte(self, channels: List[Dict[str, Any]]) -> None:
        template_path = _join(self.template_dir, "channel-lte.cha")
        dest_path = _join(self.swat_txtinout_dir, "channel-lte.cha")
        if not _exists(template_path):
            return
        with open(template_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return

        header = lines[1]
        sample = lines[2].split()
        if len(sample) < 5:
            return
        cha_ini = sample[2]
        cha_sed = sample[4] if len(sample) > 4 else "null"
        cha_nut = sample[5] if len(sample) > 5 else "nutcha1"

        width = max(2, len(str(max(ch["chn_enum"] for ch in channels))))

        output = [lines[0], header]
        for channel in channels:
            chn_enum = channel["chn_enum"]
            name = f"cha{chn_enum:0{width}d}"
            hyd_name = f"hydcha{chn_enum:0{width}d}"
            output.append(
                f"{chn_enum:>8} {name:>6} {cha_ini:>12} {hyd_name:>15} {cha_sed:>12} {cha_nut:>12}"
            )

        with open(dest_path, "w") as handle:
            handle.write("\n".join(output) + "\n")

    def _write_hyd_sed_lte(self, channels: List[Dict[str, Any]]) -> None:
        template_path = _join(self.template_dir, "hyd-sed-lte.cha")
        dest_path = _join(self.swat_txtinout_dir, "hyd-sed-lte.cha")
        if not _exists(template_path):
            return

        with open(template_path) as handle:
            lines = handle.read().splitlines()
        if len(lines) < 3:
            return

        header_line = lines[1]
        header = header_line.split()
        sample = lines[2].split()
        if len(sample) < len(header):
            sample.extend([""] * (len(header) - len(sample)))
        defaults = dict(zip(header, sample))

        width = max(2, len(str(max(ch["chn_enum"] for ch in channels))))

        output = [lines[0], header_line]
        for channel in channels:
            chn_enum = channel["chn_enum"]
            name = f"hydcha{chn_enum:0{width}d}"
            values = defaults.copy()
            values["name"] = name
            values["order"] = str(channel["order"])
            values["wd"] = f"{channel['width_m']:.5f}"
            values["dp"] = f"{channel['depth_m']:.5f}"
            values["slp"] = f"{channel['slope']:.5f}"
            values["len"] = f"{channel['length_km']:.5f}"
            values["mann"] = f"{self.channel_params['mann']:.5f}"
            values["erod_fact"] = f"{self.channel_params['erod_fact']:.5f}"
            values["cov_fact"] = f"{self.channel_params['cov_fact']:.5f}"
            values["d50"] = f"{self.channel_params['d50_mm']:.5f}"
            values["wd_rto"] = f"{channel['wd_rto']:.5f}"

            if self.channel_params.get("fpn") is not None:
                values["fpn"] = f"{self.channel_params['fpn']:.5f}"

            row = " ".join(values.get(col, "") for col in header)
            output.append(row)

        with open(dest_path, "w") as handle:
            handle.write("\n".join(output) + "\n")

    def _collect_run_outputs(self, start_time: float) -> List[str]:
        output_files: List[str] = []
        for root, _, files in os.walk(self.swat_txtinout_dir):
            for name in files:
                path = _join(root, name)
                try:
                    if os.path.getmtime(path) < start_time:
                        continue
                except OSError:
                    continue
                rel = os.path.relpath(path, self.swat_txtinout_dir)
                output_files.append(rel)
        return output_files

    def _copy_outputs(self, output_files: List[str], run_dir: str) -> List[str]:
        copied: List[str] = []
        for rel in output_files:
            src = _join(self.swat_txtinout_dir, rel)
            dest = _join(run_dir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                shutil.copy2(src, dest)
            except FileNotFoundError:
                continue
            copied.append(rel)
        return copied

    def _resolve_swat_bin(self) -> str:
        default = _join(
            os.path.dirname(__file__),
            'bin',
            'swatplus-61.0.2.61-17-g834fad2-gnu-lin_x86_64',
        )
        path = self.config_get_path('swat', 'swat_bin', default)
        return os.path.abspath(path) if path is not None else default

    def _resolve_template_dir(self) -> str:
        default = _join(os.path.dirname(__file__), 'templates', 'ref_1hru')
        path = self.config_get_path('swat', 'swat_template_dir', default)
        return os.path.abspath(path) if path is not None else default

    def _resolve_latest_run_dir(self, run_dir: Optional[str]) -> Optional[str]:
        if run_dir is not None:
            return run_dir
        if self.run_summary and self.run_summary.get("run_id"):
            return _join(self.swat_outputs_dir, f"run_{self.run_summary['run_id']}")
        if not _exists(self.swat_outputs_dir):
            return None
        latest_path = None
        latest_mtime = None
        for entry in os.scandir(self.swat_outputs_dir):
            if not entry.is_dir():
                continue
            if not entry.name.startswith("run_"):
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if latest_mtime is None or mtime > latest_mtime:
                latest_mtime = mtime
                latest_path = entry.path
        return latest_path


def _load_rust_swat_utils() -> Tuple[Optional[object], Optional[Exception]]:
    try:
        return importlib.import_module("wepppyo3.swat_utils"), None
    except Exception as exc:
        for module_name in ("wepppyo3.swat_utils_rust", "wepppyo3.swat_utils.swat_utils_rust"):
            try:
                return importlib.import_module(module_name), None
            except Exception:
                continue
        return None, exc


def _load_rust_swat_interchange() -> Tuple[Optional[object], Optional[Exception]]:
    try:
        return importlib.import_module("wepppyo3.swat_interchange"), None
    except Exception as exc:
        for module_name in (
            "wepppyo3.swat_interchange_rust",
            "wepppyo3.swat_interchange.swat_interchange_rust",
        ):
            try:
                return importlib.import_module(module_name), None
            except Exception:
                continue
        return None, exc


def _read_parquet_columns(con: duckdb.DuckDBPyConnection, parquet_path: str) -> List[str]:
    columns_query = con.execute(
        f"SELECT * FROM read_parquet('{_escape_sql_path(parquet_path)}') LIMIT 0"
    ).description
    return [desc[0] for desc in columns_query]


def _resolve_column(columns: List[str], candidates: Tuple[str, ...], parquet_path: str) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    raise ValueError(f"Missing expected columns {candidates} in {parquet_path}")


def _resolve_column_optional(columns: List[str], candidates: Tuple[str, ...]) -> Optional[str]:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def _select_or_null(column: Optional[str], alias: str) -> str:
    if column is None:
        return f"NULL as {alias}"
    return f"{_quote_ident(column)} as {alias}"


def _infer_netw_area_units(area_key: str, fieldnames: List[str]) -> Optional[str]:
    key = area_key.lower()
    if "km2" in key or "sqkm" in key or "sq_km" in key:
        return "km2"
    if "m2" in key or "sqm" in key or "sq_m" in key:
        return "m2"

    if key in ("areaup", "area_up", "area"):
        for name in fieldnames:
            lower = name.lower()
            if lower.endswith("_m") or lower.endswith("_m2") or "length_m" in lower or "drop_m" in lower:
                return "m2"
    return None


def _safe_float(value: Any, default: Optional[float]) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _escape_sql_path(path: str) -> str:
    return path.replace("'", "''")


def _quote_ident(identifier: str) -> str:
    return f"\"{identifier.replace('\"', '\"\"')}\""


def _signal_name(returncode: int) -> Optional[str]:
    if returncode >= 0:
        return None
    try:
        return signal.Signals(-returncode).name
    except Exception:
        return None


def _tail_text(text: Optional[str], max_lines: int = 20, max_chars: int = 2000) -> str:
    if not text:
        return ""
    lines = text.rstrip().splitlines()
    tail = "\n".join(lines[-max_lines:])
    if len(tail) > max_chars:
        tail = tail[-max_chars:]
    return tail
