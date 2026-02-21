from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from wepppy.climates.cligen import ClimateFile, StationMeta


class ClimateUserDefinedStationMetaService:
    """Build StationMeta and companion PAR stub for uploaded user-defined CLI files."""

    def build_station_meta_from_cli(
        self,
        *,
        cli: ClimateFile,
        cli_filename: str,
        cli_dir: str,
        monthlies: Optional[Dict[str, List[float]]],
    ) -> StationMeta:
        desc = self._resolve_description(cli.header)
        station_id = self._resolve_station_id(cli.header, cli_filename)
        state = self._resolve_state(station_id, desc)
        elevation_ft = self._resolve_elevation_ft(cli.elevation)
        monthlies_override, annual_ppt = self._build_monthlies_override(monthlies)

        par_path = Path(cli_dir) / f"{station_id}.par"
        self._write_user_defined_par_stub(
            par_path=par_path,
            desc=desc,
            station_id=station_id,
            lat=cli.lat,
            lng=cli.lng,
            elevation_ft=elevation_ft,
            years=cli.input_years,
            monthlies_override=monthlies_override,
        )

        station_meta = StationMeta(
            state,
            desc,
            str(par_path),
            cli.lat,
            cli.lng,
            cli.input_years,
            0,
            elevation_ft,
            None,
            None,
            annual_ppt,
        )
        if monthlies_override is not None:
            station_meta._monthlies_override = monthlies_override
        return station_meta

    @staticmethod
    def _resolve_description(header: List[str]) -> str:
        for line in header:
            if re.match(r"\s*Station\s*:", line, re.IGNORECASE):
                desc = line.split(":", 1)[1].strip()
                if "CLIGEN VER." in desc:
                    desc = desc.split("CLIGEN VER.", 1)[0].strip()
                return desc
        return "User defined climate"

    @staticmethod
    def _resolve_station_id(header: List[str], cli_filename: str) -> str:
        for line in header:
            match = re.search(r"([A-Za-z0-9._/\\\\-]+\\.par)", line, re.IGNORECASE)
            if not match:
                continue
            token = match.group(1).strip()
            if token.startswith("-"):
                token = token.lstrip("-")
                if token.lower().startswith("i") and token[1:].lower().endswith(".par"):
                    token = token[1:]
            station_id = Path(token).stem
            break
        else:
            station_id = Path(cli_filename).stem

        return re.sub(r"[^A-Za-z0-9_-]+", "", station_id) or "user_defined"

    @staticmethod
    def _resolve_state(station_id: str, desc: str) -> str:
        if len(station_id) >= 2 and station_id[:2].isalpha():
            return station_id[:2].upper()

        tokens = desc.split()
        if tokens and len(tokens[-1]) == 2 and tokens[-1].isalpha():
            return tokens[-1].upper()
        return "NA"

    @staticmethod
    def _resolve_elevation_ft(elevation_m: Optional[float]) -> Optional[float]:
        if elevation_m is None:
            return None
        return round(elevation_m / 0.3048, 2)

    @staticmethod
    def _build_monthlies_override(
        monthlies: Optional[Dict[str, List[float]]],
    ) -> tuple[Optional[Dict[str, List[float]]], Optional[float]]:
        if not monthlies:
            return None, None

        monthly_ppts = [float(v) for v in monthlies.get("ppts", [])]
        nwds = [float(v) for v in monthlies.get("nwds", [])]
        tmaxs = [float(v) for v in monthlies.get("tmaxs", [])]
        tmins = [float(v) for v in monthlies.get("tmins", [])]

        ppts_per_wet_day: List[float] = []
        for ppt, nwd in zip(monthly_ppts, nwds):
            ppts_per_wet_day.append(ppt / nwd if nwd else 0.0)

        return (
            {
                "ppts": ppts_per_wet_day,
                "nwds": nwds,
                "tmaxs": tmaxs,
                "tmins": tmins,
            },
            float(sum(monthly_ppts)),
        )

    def _write_user_defined_par_stub(
        self,
        *,
        par_path: Path,
        desc: str,
        station_id: str,
        lat: float,
        lng: float,
        elevation_ft: Optional[float],
        years: Optional[int],
        monthlies_override: Optional[Dict[str, List[float]]],
    ) -> None:
        if par_path.exists():
            return

        ppts = monthlies_override.get("ppts", []) if monthlies_override else []
        tmaxs = monthlies_override.get("tmaxs", []) if monthlies_override else []
        tmins = monthlies_override.get("tmins", []) if monthlies_override else []
        zeros = [0.0] * 12

        elev_ft = elevation_ft if elevation_ft is not None else 0.0
        years_val = int(years or 0)
        desc_line = f"{desc} {station_id} 0".strip()

        lines = [
            f"{desc_line}\n",
            f" LATT= {lat:7.2f} LONG={lng:7.2f} YEARS= {years_val:2d}. TYPE= 0\n",
            f" ELEVATION = {elev_ft:.0f}. TP5 = 0.00 TP6= 0.00\n",
            self._format_par_line("MEAN P", ppts),
            self._format_par_line("S DEV P", zeros),
            self._format_par_line("SKEW  P", zeros),
            self._format_par_line("P(W/W)", zeros),
            self._format_par_line("P(W/D)", zeros),
            self._format_par_line("TMAX AV", tmaxs),
            self._format_par_line("TMIN AV", tmins),
        ]
        par_path.write_text("".join(lines))

    @staticmethod
    def _format_par_line(label: str, values: List[float]) -> str:
        values = list(values)
        if len(values) < 12:
            values.extend([0.0] * (12 - len(values)))
        elif len(values) > 12:
            values = values[:12]
        values_str = "".join(f"{value:6.2f}" for value in values)
        return f"{label:<8}{values_str}\n"
