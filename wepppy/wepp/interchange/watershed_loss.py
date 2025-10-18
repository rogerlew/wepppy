from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import ast
import math

import pandas as pd
import pyarrow.parquet as pq

from wepppy.all_your_base import find_ranges
from wepppy.wepp.interchange.watershed_loss_interchange import run_wepp_watershed_loss_interchange


AVERAGE_FILENAMES = {
    "hill": "loss_pw0.hill.parquet",
    "chn": "loss_pw0.chn.parquet",
    "out": "loss_pw0.out.parquet",
    "class_data": "loss_pw0.class_data.parquet",
}

def _ensure_interchange_assets(output_dir: Path) -> Dict[str, Path]:
    assets = {}
    for key, filename in AVERAGE_FILENAMES.items():
        path = output_dir / "interchange" / filename
        assets[key] = path if path.exists() else None

    if not all(assets.values()):
        run_wepp_watershed_loss_interchange(output_dir)
        for key, filename in AVERAGE_FILENAMES.items():
            path = output_dir / "interchange" / filename
            if not path.exists():
                raise FileNotFoundError(f"Missing watershed loss interchange product: {filename}")
            assets[key] = path

    return assets


def _read_table(path: Path) -> Tuple[pd.DataFrame, Dict[bytes, bytes]]:
    table = pq.read_table(path)
    metadata = dict(table.schema.metadata or {})
    frame = table.to_pandas()
    return frame, metadata


def _augment_hill_channel_frames(
    hill_df: pd.DataFrame,
    chn_df: pd.DataFrame,
    wd: Optional[str],
    has_phosphorus: bool,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if wd is None:
        return hill_df, chn_df

    from wepppy.nodb.core import Landuse, Soils, Watershed

    hill_df = hill_df.copy()
    chn_df = chn_df.copy()

    landuse = Landuse.getInstance(wd)
    soils = Soils.getInstance(wd)
    watershed = Watershed.getInstance(wd)
    translator = watershed.translator_factory()

    hill_id_column = next((name for name in ("wepp_id", "WeppID", "weppId", "Hillslopes") if name in hill_df.columns), None)
    if hill_id_column is None:
        columns = ", ".join(hill_df.columns)
        raise KeyError(
            "Hillslope loss table missing WEPP identifier column (expected one of wepp_id, WeppID, weppId, Hillslopes); "
            f"columns={columns}"
        )

    chn_id_column = next((name for name in ("chn_enum", "Channels and Impoundments") if name in chn_df.columns), None)
    if chn_id_column is None:
        columns = ", ".join(chn_df.columns)
        raise KeyError(
            "Channel loss table missing channel identifier column (expected one of chn_enum, Channels and Impoundments); "
            f"columns={columns}"
        )

    hill_ids = pd.to_numeric(hill_df[hill_id_column], errors="coerce").astype("Int64")
    chn_ids = pd.to_numeric(chn_df[chn_id_column], errors="coerce").astype("Int64")

    hill_df["wepp_id"] = hill_ids
    hill_df["WeppID"] = hill_ids
    hill_df["Hillslopes"] = hill_ids

    if "chn_enum" not in chn_df.columns:
        chn_df["chn_enum"] = chn_ids
    else:
        chn_df["chn_enum"] = chn_ids
    chn_df["Channels and Impoundments"] = chn_ids
    if "wepp_id" not in chn_df.columns:
        chn_df["wepp_id"] = pd.Series(pd.NA, index=chn_df.index, dtype="Int64")
    else:
        chn_df["wepp_id"] = pd.to_numeric(chn_df["wepp_id"], errors="coerce").astype("Int64")

    for idx, row in hill_df.iterrows():
        wepp_raw = hill_ids.iat[idx]
        if pd.isna(wepp_raw):
            continue
        wepp_id = int(wepp_raw)
        topaz_id = translator.top(wepp=wepp_id)

        area = float(row.get("Hillslope Area", 0.0) or 0.0)
        if area == 0.0:
            area = watershed.hillslope_area(topaz_id) * 1e-4

        hill_df.at[idx, "Hillslopes"] = wepp_id
        hill_df.at[idx, "WeppID"] = wepp_id
        hill_df.at[idx, "wepp_id"] = wepp_id
        hill_df.at[idx, "TopazID"] = topaz_id
        hill_df.at[idx, "topaz_id"] = topaz_id
        hill_df.at[idx, "Landuse"] = landuse.domlc_d.get(str(topaz_id))
        hill_df.at[idx, "Soil"] = soils.domsoil_d.get(str(topaz_id))
        hill_df.at[idx, "Length"] = watershed.hillslope_length(topaz_id)

        denom = area * 1000.0
        for source, target in (
            ("Runoff Volume", "Runoff"),
            ("Subrunoff Volume", "Subrunoff"),
            ("Baseflow Volume", "Baseflow"),
        ):
            value = row.get(source)
            value = float(value) if value not in (None, "") else math.nan
            hill_df.at[idx, target] = math.nan if denom == 0 else 100.0 * value / denom

        soil_loss = float(row.get("Soil Loss", math.nan) or math.nan)
        sed_dep = float(row.get("Sediment Deposition", math.nan) or math.nan)
        sed_yield = float(row.get("Sediment Yield", math.nan) or math.nan)

        density_denominator = area if area else math.nan
        for source, target in (
            (soil_loss, "Soil Loss Density"),
            (sed_dep, "Sediment Deposition Density"),
            (sed_yield, "Sediment Yield Density"),
        ):
            hill_df.at[idx, target] = (
                math.nan if math.isnan(density_denominator) or density_denominator == 0 else source / density_denominator
            )

        hill_df.at[idx, "DepLoss"] = hill_df.at[idx, "Sediment Yield Density"] - hill_df.at[idx, "Sediment Deposition Density"]

        if has_phosphorus:
            for source, target in (
                ("Solub. React. Phosphorus", "Solub. React. P Density"),
                ("Particulate Phosphorus", "Particulate P Density"),
                ("Total Phosphorus", "Total P Density"),
            ):
                value = row.get(source)
                value = float(value) if value not in (None, "") else math.nan
                hill_df.at[idx, target] = (
                    math.nan if math.isnan(density_denominator) or density_denominator == 0 else value / density_denominator
                )

    for idx, row in chn_df.iterrows():
        chn_raw = chn_ids.iat[idx]
        if pd.isna(chn_raw):
            continue
        chn_id = int(chn_raw)
        topaz_id = translator.top(chn_enum=chn_id)
        wepp_channel_id = translator.wepp(chn_enum=chn_id)

        area = float(row.get("Contributing Area", 0.0) or 0.0)
        if area == 0.0:
            area = watershed.channel_area(topaz_id) / 10000.0

        chn_df.at[idx, "Channels and Impoundments"] = chn_id
        chn_df.at[idx, "chn_enum"] = chn_id
        if pd.isna(row.get("wepp_id")):
            chn_df.at[idx, "wepp_id"] = wepp_channel_id
        chn_df.at[idx, "WeppID"] = chn_id
        chn_df.at[idx, "WeppChnID"] = wepp_channel_id
        chn_df.at[idx, "TopazID"] = topaz_id
        chn_df.at[idx, "topaz_id"] = topaz_id
        chn_df.at[idx, "Area"] = area
        chn_df.at[idx, "Length"] = watershed.channel_length(topaz_id)

        density_denominator = area if area else math.nan
        for source, target in (
            ("Sediment Yield", "Sediment Yield Density"),
            ("Soil Loss", "Soil Loss Density"),
        ):
            value = row.get(source)
            value = float(value) if value not in (None, "") else math.nan
            chn_df.at[idx, target] = (
                math.nan if math.isnan(density_denominator) or density_denominator == 0 else value / density_denominator
            )

        if has_phosphorus:
            for source, target in (
                ("Solub. React. Phosphorus", "Solub. React. P Density"),
                ("Particulate Phosphorus", "Particulate P Density"),
                ("Total Phosphorus", "Total P Density"),
            ):
                value = row.get(source)
                value = float(value) if value not in (None, "") else math.nan
                chn_df.at[idx, target] = (
                    math.nan if math.isnan(density_denominator) or density_denominator == 0 else value / density_denominator
                )

    return hill_df, chn_df



class Loss:
    def __init__(
        self,
        fn: str | Path,
        has_phosphorus: bool = False,
        wd: Optional[str] = None
    ) -> None:
        self.fn = str(fn)
        self.has_phosphorus = has_phosphorus

        base_path = Path(fn)
        if base_path.is_dir():
            raise ValueError("Loss expects a file path to loss_pw0.txt, not a directory.")

        output_dir = base_path.parent
        assets = _ensure_interchange_assets(output_dir)

        hill_df, hill_meta = _read_table(assets["hill"])
        chn_df, chn_meta = _read_table(assets["chn"])
        out_df, _ = _read_table(assets["out"])
        class_df, _ = _read_table(assets["class_data"])

        hill_df, chn_df = _augment_hill_channel_frames(hill_df, chn_df, wd, has_phosphorus)

        self._hill_df = hill_df
        self._chn_df = chn_df
        self._out_df = out_df.copy()
        self.class_data = class_df.to_dict("records")

        outlet_row = self._out_df[self._out_df["key"] == "Total contributing area to outlet"]
        if not outlet_row.empty:
            area_value = outlet_row.iloc[0].get("value", outlet_row.iloc[0].get("v"))
            self.wsarea = float(area_value) if area_value is not None else math.nan
        else:
            self.wsarea = math.nan

    @property
    def hill_tbl(self) -> List[Dict[str, object]]:
        return self._hill_df.to_dict("records")

    @property
    def chn_tbl(self) -> List[Dict[str, object]]:
        return self._chn_df.to_dict("records")

    @property
    def out_tbl(self) -> List[Dict[str, object]]:
        records: List[Dict[str, object]] = []
        for row in self._out_df.to_dict("records"):
            value = row.get("value", row.get("v"))
            records.append({
                "key": row.get("key"),
                "value": value,
                "v": value,
                "units": row.get("units"),
            })
        return records

    def outlet_fraction_under(self, particle_size: float = 0.016) -> float:
        if not self.class_data:
            return 0.0

        class_data = []
        for row in self.class_data:
            diameter = row.get("Diameter")
            fraction = row.get("Fraction In Flow Exiting")
            try:
                diameter = float(diameter)
                fraction = float(fraction)
            except (TypeError, ValueError):
                continue
            if math.isnan(diameter) or math.isnan(fraction):
                continue
            class_data.append((diameter, fraction))

        class_data.sort(key=lambda item: item[0])

        if not class_data:
            return 0.0

        if particle_size >= class_data[-1][0]:
            return 1.0

        lower_diameter = 0.0
        cumulative = 0.0

        for diameter, fraction in class_data:
            if particle_size <= diameter:
                span = diameter - lower_diameter
                if span <= 0:
                    return cumulative
                return cumulative + (particle_size - lower_diameter) / span * fraction
            cumulative += fraction
            lower_diameter = diameter

        return cumulative


__all__ = ["Loss"]
