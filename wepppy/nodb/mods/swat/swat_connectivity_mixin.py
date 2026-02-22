"""Channel loading and connectivity writers for SWAT NoDb."""

from __future__ import annotations

import csv
from os.path import exists as _exists
from os.path import join as _join
from typing import Any, Dict, List, Optional

import duckdb

from wepppy.nodir.parquet_sidecars import pick_existing_parquet_path
from wepppy.topo.peridot.peridot_runner import read_network

from ._helpers import (
    _escape_sql_path,
    _infer_netw_area_units,
    _quote_ident,
    _read_parquet_columns,
    _resolve_column,
    _resolve_column_optional,
    _safe_float,
    _select_or_null,
)
from .errors import SwatNoDbLockedException


class SwatConnectivityMixin:
    def _load_channels(self) -> List[Dict[str, Any]]:
        channels_path = pick_existing_parquet_path(self.wd, "watershed/channels.parquet")
        if channels_path is None:
            raise FileNotFoundError("Missing channels parquet (watershed/channels.parquet)")
        channels_parquet = str(channels_path)

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

