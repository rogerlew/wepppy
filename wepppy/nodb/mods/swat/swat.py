"""SWAT+ NoDb controller.

Implements recall generation, TxtInOut assembly, and SWAT+ execution for
WEPP hillslope pass routing through SWAT-DEG channels.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
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
from wepppy.nodir.parquet_sidecars import pick_existing_parquet_path
from wepppy.nodb.mods.swat._helpers import (
    _escape_sql_path,
    _quote_ident,
    _read_parquet_columns,
    _resolve_column,
    _resolve_column_optional,
    _select_or_null,
    _signal_name,
    _tail_text,
)
from wepppy.nodb.mods.swat.errors import SwatNoDbLockedException
from wepppy.nodb.mods.swat.swat_connectivity_mixin import SwatConnectivityMixin
from wepppy.nodb.mods.swat.swat_recall_mixin import SwatRecallMixin
from wepppy.nodb.mods.swat.swat_txtinout_mixin import SwatTxtInOutMixin
from wepppy.wepp.interchange._rust_interchange import resolve_cli_calendar_path, version_args
from wepppy.wepp.interchange._utils import CalendarLookup
from wepppy.nodb.status_messenger import StatusMessenger

__all__ = [
    'SwatNoDbLockedException',
    'Swat',
]


class Swat(SwatTxtInOutMixin, SwatRecallMixin, SwatConnectivityMixin, NoDbBase):
    __name__ = 'Swat'
    _CHANNEL_PARAM_FIELDS = {
        'channel_mann': 'mann',
        'channel_fpn': 'fpn',
        'channel_erod_fact': 'erod_fact',
        'channel_cov_fact': 'cov_fact',
        'channel_d50_mm': 'd50_mm',
    }

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

    def _parse_channel_param_updates(self, kwds: Dict[str, Any]) -> Dict[str, Optional[float]]:
        def _coerce_scalar(value: Any) -> Any:
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    if item not in (None, '', False):
                        return item
                return ''
            return value

        updates: Dict[str, Optional[float]] = {}
        for input_key, param_key in self._CHANNEL_PARAM_FIELDS.items():
            if input_key not in kwds:
                continue
            raw_value = _coerce_scalar(kwds.get(input_key))
            if raw_value in (None, '', False):
                if input_key == 'channel_fpn':
                    updates[param_key] = None
                continue
            try:
                parsed = float(raw_value)
            except (TypeError, ValueError):
                continue
            updates[param_key] = parsed
        return updates

    def parse_inputs(self, kwds: Dict[str, Any]) -> None:
        updates = self._parse_channel_param_updates(kwds)
        if not updates:
            return
        with self.locked():
            if not isinstance(getattr(self, 'channel_params', None), dict):
                self.channel_params = {}
            for key, value in updates.items():
                self.channel_params[key] = value

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
        hillslopes_path = pick_existing_parquet_path(self.wd, "watershed/hillslopes.parquet")
        channels_path = pick_existing_parquet_path(self.wd, "watershed/channels.parquet")
        if hillslopes_path is None:
            raise FileNotFoundError("Missing hillslopes parquet (watershed/hillslopes.parquet)")
        if channels_path is None:
            raise FileNotFoundError("Missing channels parquet (watershed/channels.parquet)")

        hillslopes_parquet = str(hillslopes_path)
        channels_parquet = str(channels_path)

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
            except (OSError, ValueError, TypeError):
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
        except (OSError, ValueError, TypeError) as exc:
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
    except ImportError as exc:
        for module_name in ("wepppyo3.swat_utils_rust", "wepppyo3.swat_utils.swat_utils_rust"):
            try:
                return importlib.import_module(module_name), None
            except ImportError:
                continue
        return None, exc


def _load_rust_swat_interchange() -> Tuple[Optional[object], Optional[Exception]]:
    try:
        return importlib.import_module("wepppyo3.swat_interchange"), None
    except ImportError as exc:
        for module_name in (
            "wepppyo3.swat_interchange_rust",
            "wepppyo3.swat_interchange.swat_interchange_rust",
        ):
            try:
                return importlib.import_module(module_name), None
            except ImportError:
                continue
        return None, exc
