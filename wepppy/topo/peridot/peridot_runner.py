import logging
import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
import shutil

import math
import numpy as np
import pandas as pd

from subprocess import Popen, PIPE

from.flowpath import PeridotFlowpath, PeridotHillslope, PeridotChannel

try:
    from wepppy.query_engine import update_catalog_entry as _update_catalog_entry
except Exception:  # pragma: no cover - optional catalog support
    _update_catalog_entry = None

LOGGER = logging.getLogger(__name__)


_thisdir = os.path.dirname(__file__)


def _get_bin():
    _bin = _join(_thisdir, 'bin', 'abstract_watershed')
    
    if not _exists(_bin):
        raise RuntimeError('abstract_watershed binary not found')
    return _bin

def _get_wbt_bin():
    _bin = _join(_thisdir, 'bin', 'wbt_abstract_watershed')

    if not _exists(_bin):
        raise RuntimeError('wbt_abstract_watershed binary not found')
    return _bin

def _get_wbt_sub_field_bin():
    _bin = _join(_thisdir, 'bin', 'sub_fields_abstraction')

    if not _exists(_bin):
        raise RuntimeError('sub_fields_abstraction binary not found')
    return _bin

def run_peridot_abstract_watershed(
    wd: str,
    clip_hillslopes: bool = True,
    clip_hillslope_length: float = 300.0,
    bieger2015_widths: bool = False,
    verbose: bool = True
):
    assert _exists(_join(wd, 'dem/topaz/SUBWTA.ARC'))

    cmd = [_get_bin(), wd, '--ncpu', '24']

    if clip_hillslopes:
        assert clip_hillslope_length > 0.0
        cmd += ['--clip-hillslopes', '--clip-hillslope-length', str(clip_hillslope_length)]

    if bieger2015_widths:
        cmd += ['--bieger2015-widths']

    if verbose:
        print(' '.join(cmd))

    _log = open(_join(wd, '_peridot.log'), 'w')
    p = Popen(cmd, stdout=_log, stderr=_log)
    p.wait()

def run_peridot_wbt_abstract_watershed(
    wd: str,
    clip_hillslopes: bool = True,
    clip_hillslope_length: float = 300.0,
    bieger2015_widths: bool = False,
    verbose: bool = True
):
    """
    Run the Peridot abstract watershed tool using WhiteboxTools.
    
    Parameters:
        wd (str): Working directory where the Topaz data is located.
        clip_hillslopes (bool): Whether to clip hillslopes.
        clip_hillslope_length (float): Length to clip hillslopes.
        bieger2015_widths (bool): Whether to use Bieger 2015 widths.
        verbose (bool): If True, print command details.
    """
    assert _exists(_join(wd, 'dem/wbt/subwta.tif'))

    cmd = [_get_wbt_bin(), wd, '--ncpu', '24']

    if clip_hillslopes:
        assert clip_hillslope_length > 0.0
        cmd += ['--clip-hillslopes', '--clip-hillslope-length', str(clip_hillslope_length)]

    if bieger2015_widths:
        cmd += ['--bieger2015-widths']

    if verbose:
        print(' '.join(cmd))

    _log = open(_join(wd, '_peridot.log'), 'w')
    p = Popen(cmd, stdout=_log, stderr=_log)
    p.wait()


def post_abstract_watershed(wd: str, verbose: bool = True):
    """
    Post-process the output of the Peridot abstract watershed tool.

    calculate and return ws_cenroid and ws_area
    """

    from wepppy.topo.watershed_abstraction import WeppTopTranslator

    hill_df = pd.read_csv(_join(wd, 'watershed/hillslopes.csv'))
    sub_ids = sorted([int(x) for x in hill_df['topaz_id']])

    chn_df = pd.read_csv(_join(wd, 'watershed/channels.csv'))
    chn_ids = sorted([int(x) for x in  chn_df['topaz_id']])

    translator = WeppTopTranslator(sub_ids, chn_ids)
    get_wepp_id = lambda topaz_id: translator.wepp(topaz_id)
    get_chn_enum = lambda topaz_id: translator.chn_enum(top=topaz_id)
    
    hill_df['topaz_id'] = pd.to_numeric(hill_df['topaz_id'], errors='raise').astype('Int32')
    hill_df['wepp_id'] = hill_df['topaz_id'].apply(lambda top: get_wepp_id(int(top))).astype('Int32')

    hill_df.to_parquet(_join(wd, 'watershed/hillslopes.parquet'), index=False)
    sub_area = float(hill_df['area'].sum())
    lngs = hill_df['centroid_lon'].to_numpy()
    lats = hill_df['centroid_lat'].to_numpy()

    chn_df['topaz_id'] = pd.to_numeric(chn_df['topaz_id'], errors='raise').astype('Int32')
    chn_df['wepp_id'] = chn_df['topaz_id'].apply(lambda top: get_wepp_id(int(top))).astype('Int32')
    chn_df['chn_enum'] = chn_df['topaz_id'].apply(lambda top: get_chn_enum(int(top))).astype('Int32')

    chn_df.to_parquet(_join(wd, 'watershed/channels.parquet'), index=False)
    chn_area = float(chn_df['area'].sum())
    lngs = np.concatenate((lngs, chn_df['centroid_lon'].to_numpy()))
    lats = np.concatenate((lats, chn_df['centroid_lat'].to_numpy()))

    fps_df = pd.read_csv(_join(wd, 'watershed/flowpaths.csv'))
    fps_df['topaz_id'] = pd.to_numeric(fps_df['topaz_id'], errors='raise').astype('Int32')
    fps_df['fp_id'] = pd.to_numeric(fps_df['fp_id'], errors='raise').astype('Int32')
    fps_df.to_parquet(_join(wd, 'watershed/flowpaths.parquet'), index=False)

    os.remove(_join(wd, 'watershed/hillslopes.csv'))
    os.remove(_join(wd, 'watershed/channels.csv')) 
    os.remove(_join(wd, 'watershed/flowpaths.csv'))

    if _update_catalog_entry is not None:
        try:
            _update_catalog_entry(wd, 'watershed')
        except Exception:  # pragma: no cover - catalog refresh best effort
            LOGGER.warning("Failed to refresh catalog for watershed outputs in %s", wd, exc_info=True)

    ws_centroid = float(np.mean(lngs)), float(np.mean(lats))
    return sub_area, chn_area, ws_centroid, sub_ids, chn_ids


def read_network(fname):
    with open(fname) as fp:
        lines = fp.readlines()

    network = {}
    for L in lines:
        k, vals = L.split('|')
        network[int(k)] = [int(v) for v in vals.split(',')]

    return network

def run_peridot_wbt_sub_fields_abstraction(
    wd: str,
    clip_hillslopes: bool = True,
    clip_hillslope_length: float = 300.0,
    sub_field_min_area_threshold_m2: float = 0.0,
    verbose: bool = True
):
    """
    Run the Peridot abstract watershed tool using WhiteboxTools.

    Parameters:
        wd (str): Working directory where the Topaz data is located.
        clip_hillslopes (bool): Whether to clip hillslopes.
        clip_hillslope_length (float): Length to clip hillslopes.
        sub_field_min_area_threshold_m2 (float): Minimum area threshold for sub-fields.
        verbose (bool): If True, print command details.
    """
    assert _exists(_join(wd, 'dem/wbt/flovec.tif')), 'dem/wbt/flovec.tif not found'
    assert _exists(_join(wd, 'ag_fields/field_boundaries.tif')), 'ag_fields/field_boundaries.tif not found'

    cmd = [_get_wbt_sub_field_bin(), wd, '--ncpu', '24']

    if clip_hillslopes:
        assert clip_hillslope_length > 0.0
        cmd += ['--clip-hillslopes', '--clip-hillslope-length', str(clip_hillslope_length)]

    if sub_field_min_area_threshold_m2 > 0.0:
        cmd += ['--sub-field-min-area-threshold-m2', str(sub_field_min_area_threshold_m2)]

    if verbose:
        print(' '.join(cmd))

    _log = open(_join(wd, '_peridot.log'), 'w')
    p = Popen(cmd, stdout=_log, stderr=_log)
    p.wait()


def post_abstract_sub_fields(wd: str, verbose: bool = True):
    """
    Post-process the output of the Peridot abstract watershed tool.

    calculate and return ws_cenroid and ws_area
    """

    from wepppy.nodb.core import Watershed

    field_df = pd.read_csv(_join(wd, 'ag_fields/sub_fields/fields.csv'))

    translator = Watershed.getInstance(wd).translator_factory()
    get_wepp_id = lambda topaz_id: translator.wepp(topaz_id)
    field_df['topaz_id'] = pd.to_numeric(field_df['topaz_id'], errors='raise').astype('Int32')
    field_df['wepp_id'] = field_df['topaz_id'].apply(lambda top: get_wepp_id(int(top))).astype('Int32')
    field_df.to_parquet(_join(wd, 'ag_fields/sub_fields/fields.parquet'), index=False)

    fps_df = pd.read_csv(_join(wd, 'ag_fields/sub_fields/field_flowpaths.csv'))
    fps_df['topaz_id'] = pd.to_numeric(fps_df['topaz_id'], errors='raise').astype('Int32')
    fps_df['fp_id'] = pd.to_numeric(fps_df['fp_id'], errors='raise').astype('Int32')
    fps_df.to_parquet(_join(wd, 'ag_fields/sub_fields/field_flowpaths.parquet'), index=False)

    os.remove(_join(wd, 'ag_fields/sub_fields/field_flowpaths.csv'))
    os.remove(_join(wd, 'ag_fields/sub_fields/fields.csv'))

    if _update_catalog_entry is not None:
        try:
            _update_catalog_entry(wd, 'ag_fields/sub_fields')
        except Exception:  # pragma: no cover - catalog refresh best effort
            LOGGER.warning("Failed to refresh catalog for ag_fields/sub_fields in %s", wd, exc_info=True)

    return len(field_df), len(fps_df)


def _load_watershed_table(watershed_dir, stem: str):
    from pathlib import Path

    csv_path = Path(watershed_dir, f"{stem}.csv")
    parquet_path = Path(watershed_dir, f"{stem}.parquet")

    if csv_path.exists():
        return pd.read_csv(csv_path), csv_path
    if parquet_path.exists():
        return pd.read_parquet(parquet_path), parquet_path
    return None, None


def _coerce_series_to_int32(series: pd.Series, name: str) -> pd.Series:
    values = []
    for raw in series:
        if pd.isna(raw):
            raise ValueError(f"{name} contains null values; cannot coerce to Int32")

        if isinstance(raw, (int, np.integer)):
            values.append(int(raw))
            continue

        if isinstance(raw, (float, np.floating)):
            if not float(raw).is_integer():
                raise ValueError(f"{name} value {raw!r} is not an integer")
            values.append(int(raw))
            continue

        text = str(raw).strip()
        try:
            values.append(int(text))
            continue
        except ValueError:
            try:
                flt = float(text)
            except ValueError as exc:
                raise ValueError(f"{name} value {raw!r} cannot be parsed as integer") from exc
            if not math.isfinite(flt) or not flt.is_integer():
                raise ValueError(f"{name} value {raw!r} is not an integer")
            values.append(int(flt))

    return pd.Series(pd.array(values, dtype="Int32"), index=series.index, name=name)


def _extract_int32_column(df: pd.DataFrame, primary: str, fallbacks=(), *, allow_missing: bool = False):
    for col in (primary, *fallbacks):
        if col in df.columns:
            return _coerce_series_to_int32(df[col], primary)

    if allow_missing:
        return None

    raise KeyError(f"{primary} column not found (searched {primary!r} + {fallbacks!r})")


def migrate_watershed_outputs(wd: str, *, remove_csv: bool = True, verbose: bool = False) -> bool:
    """
    Standardize watershed tables for peridot-derived abstractions.

    Converts identifier columns to Int32 and rewrites parquet outputs. Legacy CSV
    artifacts are upgraded in-place.
    """
    from pathlib import Path
    from wepppy.nodb.core import Watershed
    from wepppy.topo.watershed_abstraction import WeppTopTranslator

    root = Path(wd).expanduser()
    watershed_dir = root / "watershed"
    if not watershed_dir.exists():
        if verbose:
            print(f"[migrate_watershed_outputs] Skipping {wd}: watershed directory missing")
        return False

    watershed = Watershed.getInstance(wd)
    if not (watershed.delineation_backend_is_topaz or watershed.delineation_backend_is_wbt):
        if verbose:
            print(f"[migrate_watershed_outputs] Skipping {wd}: not a Peridot abstraction backend")
        return False

    hill_df_raw, hill_source = _load_watershed_table(watershed_dir, "hillslopes")
    chn_df_raw, chn_source = _load_watershed_table(watershed_dir, "channels")
    fp_df_raw, fp_source = _load_watershed_table(watershed_dir, "flowpaths")

    if hill_df_raw is None and chn_df_raw is None and fp_df_raw is None:
        if verbose:
            print(f"[migrate_watershed_outputs] Skipping {wd}: no watershed tables found")
        return False

    if hill_df_raw is None:
        raise RuntimeError("Hillslope table required for migration, but none found.")

    hill_topaz_series = _extract_int32_column(hill_df_raw, "topaz_id", ("TopazID",))
    if chn_df_raw is not None:
        chn_topaz_series = _extract_int32_column(chn_df_raw, "topaz_id", ("TopazID",))
        chn_ids = [int(x) for x in chn_topaz_series.dropna()]
    else:
        chn_topaz_series = None
        chn_ids = []

    sub_ids = [int(x) for x in hill_topaz_series.dropna()]
    translator = WeppTopTranslator(sub_ids, chn_ids)

    modified = False

    hill_df = hill_df_raw.copy()
    hill_df["topaz_id"] = hill_topaz_series
    wepp_series = _extract_int32_column(hill_df, "wepp_id", ("WeppID",), allow_missing=True)
    if wepp_series is None:
        wepp_values = [translator.wepp(top=int(top)) for top in hill_df["topaz_id"]]
        hill_df["wepp_id"] = pd.Series(pd.array(wepp_values, dtype="Int32"), index=hill_df.index)
    else:
        hill_df["wepp_id"] = wepp_series
    for legacy_col in ("TopazID", "WeppID"):
        if legacy_col in hill_df.columns:
            hill_df.drop(columns=[legacy_col], inplace=True)
    hill_target = watershed_dir / "hillslopes.parquet"
    hill_df.to_parquet(hill_target, index=False)
    modified = True
    if remove_csv and hill_source is not None and hill_source.suffix.lower() == ".csv":
        try:
            hill_source.unlink()
        except FileNotFoundError:
            pass

    if chn_df_raw is not None:
        chn_df = chn_df_raw.copy()
        chn_df["topaz_id"] = chn_topaz_series
        chn_wepp_series = _extract_int32_column(chn_df, "wepp_id", ("WeppID",), allow_missing=True)
        if chn_wepp_series is None:
            chn_wepp_values = [translator.wepp(top=int(top)) for top in chn_df["topaz_id"]]
            chn_df["wepp_id"] = pd.Series(pd.array(chn_wepp_values, dtype="Int32"), index=chn_df.index)
        else:
            chn_df["wepp_id"] = chn_wepp_series

        chn_enum_series = _extract_int32_column(chn_df, "chn_enum", ("ChnEnum",), allow_missing=True)
        if chn_enum_series is None:
            chn_enum_values = [translator.chn_enum(top=int(top)) for top in chn_df["topaz_id"]]
            chn_df["chn_enum"] = pd.Series(pd.array(chn_enum_values, dtype="Int32"), index=chn_df.index)
        else:
            chn_df["chn_enum"] = chn_enum_series

        for legacy_col in ("TopazID", "WeppID"):
            if legacy_col in chn_df.columns:
                chn_df.drop(columns=[legacy_col], inplace=True)

        chn_target = watershed_dir / "channels.parquet"
        chn_df.to_parquet(chn_target, index=False)
        modified = True
        if remove_csv and chn_source is not None and chn_source.suffix.lower() == ".csv":
            try:
                chn_source.unlink()
            except FileNotFoundError:
                pass

    if fp_df_raw is not None:
        fp_df = fp_df_raw.copy()
        fp_df["topaz_id"] = _extract_int32_column(fp_df, "topaz_id", ("TopazID",))
        fp_df["fp_id"] = _extract_int32_column(fp_df, "fp_id", (), allow_missing=False)

        fp_target = watershed_dir / "flowpaths.parquet"
        fp_df.to_parquet(fp_target, index=False)
        modified = True
        if remove_csv and fp_source is not None and fp_source.suffix.lower() == ".csv":
            try:
                fp_source.unlink()
            except FileNotFoundError:
                pass

    if verbose:
        if modified:
            print(f"[migrate_watershed_outputs] Standardized watershed tables for {wd}")
        else:
            print(f"[migrate_watershed_outputs] No changes required for {wd}")

    return modified
