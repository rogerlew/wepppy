"""Recall conversion, calendar alignment, and time.sim patch helpers for SWAT NoDb."""

from __future__ import annotations

import os
from datetime import datetime
from os.path import exists as _exists
from os.path import join as _join
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import duckdb

from wepppy.nodir.parquet_sidecars import pick_existing_parquet_path
from wepppy.wepp.interchange._utils import CalendarLookup, _build_cli_calendar_lookup, _julian_to_calendar

from ._helpers import _escape_sql_path, _read_parquet_columns, _resolve_column_optional
from .errors import SwatNoDbLockedException


class SwatRecallMixin:
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
        hillslopes_path = pick_existing_parquet_path(self.wd, "watershed/hillslopes.parquet")
        if hillslopes_path is None:
            return None
        hillslopes_parquet = str(hillslopes_path)
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
