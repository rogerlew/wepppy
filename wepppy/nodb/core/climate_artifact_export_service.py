from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np
import pandas as pd

from wepppy.all_your_base.stats import weibull_series
from wepppy.climates.cligen import ClimateFile

if TYPE_CHECKING:
    from wepppy.nodb.core.climate import Climate


class ClimateArtifactExportService:
    """Create report-facing climate artifacts after CLI generation."""

    def export_post_build_artifacts(self, climate: "Climate") -> None:
        parquet_path = climate._export_cli_parquet()
        time.sleep(1)  # ensure parquet write is flushed
        if parquet_path is not None:
            climate._export_cli_precip_frequency_csv(parquet_path)
        climate._download_noaa_atlas14_intensity()

    def export_cli_parquet(self, climate: "Climate") -> Path | None:
        """Persist the active CLI file to parquet with peak intensities for reports."""
        cli_fn = climate.cli_fn
        if not cli_fn:
            return None

        cli_path = Path(climate.cli_dir) / cli_fn
        if not cli_path.exists():
            return None

        try:
            cli_df = ClimateFile(str(cli_path)).as_dataframe(calc_peak_intensities=True)
            export_df = cli_df.copy()
            export_df["year"] = export_df.get("year")
            export_df["month"] = export_df.get("mo")
            export_df["day_of_month"] = export_df.get("da")
            if {"year", "month", "day_of_month"}.issubset(export_df.columns):
                date_df = export_df[["year", "month", "day_of_month"]].copy()
                for col in ("year", "month", "day_of_month"):
                    date_df[col] = pd.to_numeric(date_df[col], errors="coerce")
                date_df = date_df.dropna()
                if not date_df.empty:
                    date_df["year"] = date_df["year"].astype(int)
                    date_df["month"] = date_df["month"].astype(int)
                    date_df["day_of_month"] = date_df["day_of_month"].astype(int)
                    ordered = date_df.sort_values(["year", "month", "day_of_month"])
                    ordered["julian"] = ordered.groupby("year").cumcount() + 1
                    year_counts = ordered.groupby("year")["julian"].max().sort_index()
                    offsets = year_counts.cumsum().shift(fill_value=0)
                    ordered["sim_day_index"] = ordered["julian"] + ordered["year"].map(offsets)
                    export_df["julian"] = ordered["julian"].reindex(export_df.index).astype("Int64")
                    export_df["sim_day_index"] = ordered["sim_day_index"].reindex(export_df.index).astype("Int64")

            export_df["peak_intensity_10"] = export_df.get("10-min Peak Rainfall Intensity (mm/hour)")
            export_df["peak_intensity_15"] = export_df.get("15-min Peak Rainfall Intensity (mm/hour)")
            export_df["peak_intensity_30"] = export_df.get("30-min Peak Rainfall Intensity (mm/hour)")
            export_df["peak_intensity_60"] = export_df.get("60-min Peak Rainfall Intensity (mm/hour)")

            export_df["storm_duration_hours"] = export_df.get("dur")
            export_df["storm_duration"] = export_df.get("dur")

            parquet_path = Path(climate.wd) / "climate" / "wepp_cli.parquet"
            parquet_path.parent.mkdir(parents=True, exist_ok=True)
            export_df.to_parquet(parquet_path, index=False)
            climate.logger.info("Exported CLI parquet with peak intensities", extra={"parquet": str(parquet_path)})
            return parquet_path
        # Export boundary: any parse/serialization backend error should be logged and skipped.
        except Exception:
            climate.logger.exception(
                "Failed exporting CLI parquet with peak intensities",
                extra={"cli_path": str(cli_path)},
            )
            return None

    def export_cli_precip_frequency_csv(self, climate: "Climate", parquet_path: Path) -> Optional[Path]:
        """Write NOAA-style PDS frequency stats derived from ``wepp_cli.parquet``."""
        start_time = time.time()
        if not parquet_path.exists():
            return None

        try:
            df = pd.read_parquet(parquet_path)
        # Read boundary: parquet backend/format issues are non-fatal for climate build completion.
        except Exception:
            climate.logger.exception(
                "Failed reading CLI parquet for precip frequency stats",
                extra={"parquet": str(parquet_path)},
            )
            return None
        if df.empty:
            climate.logger.info(
                "CLI parquet is empty; skipping precip frequency export",
                extra={"parquet": str(parquet_path)},
            )
            return None

        def _pick_column(candidates: Tuple[str, ...]) -> Optional[str]:
            for name in candidates:
                if name in df.columns:
                    return name
            return None

        precip_column = _pick_column(("prcp", "precip_mm", "precip", "precipitation"))
        if precip_column is None:
            climate.logger.warning(
                "CLI parquet missing precipitation column; skipping precip frequency export",
                extra={"parquet": str(parquet_path)},
            )
            return None

        df = df[df[precip_column] > 0].copy()
        if df.empty:
            climate.logger.info(
                "No precipitation events found; skipping precip frequency export",
                extra={"parquet": str(parquet_path)},
            )
            return None

        year_column = _pick_column(("year", "calendar_year"))
        if year_column is None:
            climate.logger.warning(
                "CLI parquet missing year column; skipping precip frequency export",
                extra={"parquet": str(parquet_path)},
            )
            return None

        years_count = int(pd.to_numeric(df[year_column], errors="coerce").dropna().nunique())
        if years_count <= 0:
            climate.logger.warning(
                "Unable to determine years for precip frequency export",
                extra={"parquet": str(parquet_path)},
            )
            return None

        base_recurrence = [1, 2, 5, 10, 25, 50, 100]
        recurrence = [r for r in base_recurrence if r <= years_count]
        if not recurrence:
            climate.logger.info(
                "No recurrence intervals are <= climate years; skipping precip frequency export",
                extra={"years_count": years_count, "parquet": str(parquet_path)},
            )
            return None
        rec_map = weibull_series(recurrence, years_count, method="pds")

        def _format_value(value: float) -> str:
            if value == 0 or np.isnan(value):
                return "0"
            formatted = f"{value:.2f}"
            return formatted.rstrip("0").rstrip(".")

        def _values_for(candidates: Tuple[str, ...]) -> List[float]:
            column = _pick_column(candidates)
            if column is None:
                climate.logger.info(
                    "CLI parquet missing precip frequency column",
                    extra={"column": candidates[0], "parquet": str(parquet_path)},
                )
                return [0.0] * len(recurrence)

            series = pd.to_numeric(df[column], errors="coerce")
            series = series[series > 0].dropna().sort_values(ascending=False).reset_index(drop=True)
            if series.empty:
                return [0.0] * len(recurrence)

            values: List[float] = []
            for target in recurrence:
                idx = rec_map.get(float(target), 0)
                if idx >= len(series):
                    idx = len(series) - 1
                values.append(float(series.iloc[idx]))
            return values

        rows = [
            ("Precipitation depth (mm)", _values_for((precip_column,))),
            ("Storm duration (hours)", _values_for(("storm_duration_hours", "storm_duration", "dur"))),
            (
                "10-min intensity (mm/hour)",
                _values_for(("peak_intensity_10", "10-min Peak Rainfall Intensity (mm/hour)", "i10")),
            ),
            (
                "15-min intensity (mm/hour)",
                _values_for(("peak_intensity_15", "15-min Peak Rainfall Intensity (mm/hour)", "i15")),
            ),
            (
                "30-min intensity (mm/hour)",
                _values_for(("peak_intensity_30", "30-min Peak Rainfall Intensity (mm/hour)", "i30")),
            ),
            (
                "60-min intensity (mm/hour)",
                _values_for(("peak_intensity_60", "60-min Peak Rainfall Intensity (mm/hour)", "i60")),
            ),
        ]

        monthly_medians: List[float] = [0.0] * 12
        monthly_p75s: List[float] = [0.0] * 12
        monthly_p90s: List[float] = [0.0] * 12
        month_column = _pick_column(("month", "mo"))
        intensity_column = _pick_column(("peak_intensity_30", "30-min Peak Rainfall Intensity (mm/hour)", "i30"))
        if month_column is None or intensity_column is None:
            climate.logger.info(
                "CLI parquet missing monthly median intensity columns",
                extra={
                    "month_column": month_column,
                    "intensity_column": intensity_column,
                    "parquet": str(parquet_path),
                },
            )
        else:
            monthly_df = df[[month_column, intensity_column]].copy()
            monthly_df[month_column] = pd.to_numeric(monthly_df[month_column], errors="coerce")
            monthly_df[intensity_column] = pd.to_numeric(monthly_df[intensity_column], errors="coerce")
            monthly_df = monthly_df.dropna(subset=[month_column, intensity_column])
            if not monthly_df.empty:
                monthly_df[month_column] = monthly_df[month_column].astype(int)
                medians = monthly_df.groupby(month_column)[intensity_column].median()
                p75s = monthly_df.groupby(month_column)[intensity_column].quantile(0.75)
                p90s = monthly_df.groupby(month_column)[intensity_column].quantile(0.9)
                monthly_medians = [float(medians.get(m, 0.0)) for m in range(1, 13)]
                monthly_p75s = [float(p75s.get(m, 0.0)) for m in range(1, 13)]
                monthly_p90s = [float(p90s.get(m, 0.0)) for m in range(1, 13)]

        lat_text = "None"
        lng_text = "None"
        station_name = climate.climatestation or "None"
        try:
            watershed = climate.watershed_instance
            if watershed and watershed.centroid:
                lng, lat = watershed.centroid
                lng_text = f"{float(lng):.4f} Degree"
                lat_text = f"{float(lat):.4f} Degree"
        # Metadata boundary: centroid lookup should not block CSV generation.
        except Exception:
            climate.logger.debug("Unable to resolve watershed centroid for precip frequency export", exc_info=True)

        output_path = parquet_path.with_name("wepp_cli_pds_mean_metric.csv")
        timestamp = datetime.utcnow().strftime("%a %b %d %H:%M:%S %Y")
        runtime = time.time() - start_time

        lines = [
            "Point precipitation frequency estimates (mm, hours, mm/hour)",
            "WEPP CLI derived precipitation frequency statistics",
            "Data type: Precipitation depth, storm duration, peak intensities",
            "Time series type: Partial duration",
            f"Project area: {climate.runid}",
            f"Location name (WEPP): {climate.runid}",
            f"Station Name: {station_name}",
            f"Latitude: {lat_text}",
            f"Longitude: {lng_text}",
            "Elevation (WEPP): None",
            "",
            "",
            "PRECIPITATION FREQUENCY ESTIMATES",
            "by metric for ARI (years):, " + ",".join(str(r) for r in recurrence),
        ]

        for label, values in rows:
            line_values = ",".join(_format_value(value) for value in values)
            lines.append(f"{label}:, {line_values}")

        lines.extend(
            [
                "",
                "MONTHLY MODELED MX .5 P",
                "Month:, 1,2,3,4,5,6,7,8,9,10,11,12",
                "Median (mm/hour):, " + ",".join(_format_value(value) for value in monthly_medians),
                "75th percentile (mm/hour):, " + ",".join(_format_value(value) for value in monthly_p75s),
                "90th percentile(mm/hour):, " + ",".join(_format_value(value) for value in monthly_p90s),
            ]
        )

        lines.extend(
            [
                "",
                f"Date/time (GMT):  {timestamp}",
                f"pyRunTime:  {runtime:.6f}",
            ]
        )

        try:
            output_path.write_text("\n".join(lines) + "\n")
            climate.logger.info(
                "Exported CLI precip frequency stats",
                extra={"csv": str(output_path)},
            )
            return output_path
        # Write boundary: emit telemetry and continue without the optional artifact.
        except Exception:
            climate.logger.exception(
                "Failed writing CLI precip frequency stats",
                extra={"csv": str(output_path)},
            )
            return None

    def download_noaa_atlas14_intensity(self, climate: "Climate") -> Optional[Path]:
        """Download NOAA Atlas 14 PDS mean metric intensity data for comparison."""
        cligen_db = str(climate.cligen_db or "").lower()
        if "2015" not in cligen_db and "legacy" not in cligen_db:
            return None

        output_path = Path(climate.cli_dir) / "atlas14_intensity_pds_mean_metric.csv"
        if output_path.exists():
            return output_path

        try:
            watershed = climate.watershed_instance
            if not watershed or not watershed.centroid:
                climate.logger.info(
                    "Watershed centroid unavailable; skipping NOAA Atlas 14 download",
                    extra={"cligen_db": climate.cligen_db},
                )
                return None
            lng, lat = watershed.centroid
        # Geolocation boundary: unavailable centroid should not fail the climate build.
        except Exception:
            climate.logger.exception("Failed resolving watershed centroid for NOAA Atlas 14")
            return None

        try:
            from pfdf.data.noaa import atlas14
        # Optional dependency boundary: pfdf may not be installed in all environments.
        except Exception:
            climate.logger.exception("Failed importing pfdf NOAA Atlas 14 client")
            return None

        try:
            result = atlas14.download(
                lat=float(lat),
                lon=float(lng),
                parent=str(output_path.parent),
                name=output_path.name,
                statistic="mean",
                data="intensity",
                series="pds",
                units="metric",
                timeout=30,
                overwrite=True,
            )
            if result is None:
                return None
            result_path = Path(result)
            if result_path.exists():
                climate.logger.info(
                    "Downloaded NOAA Atlas 14 intensity data",
                    extra={"csv": str(result_path)},
                )
                return result_path
        except ValueError as exc:
            climate.logger.info(
                "NOAA Atlas 14 data unavailable for location",
                extra={"error": str(exc), "lat": lat, "lon": lng},
            )
            return None
        # Network/client boundary: remote/API issues should not fail climate build completion.
        except Exception:
            climate.logger.exception(
                "Failed downloading NOAA Atlas 14 intensity data",
                extra={"lat": lat, "lon": lng},
            )
            return None

        return None
