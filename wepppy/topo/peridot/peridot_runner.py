import logging
import os
import re
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from pathlib import Path
import shutil
import time
from typing import Optional

import math
import numpy as np
import pandas as pd

from subprocess import Popen, PIPE

from.flowpath import PeridotFlowpath, PeridotHillslope, PeridotChannel
from wepppy.io_wait import (
    DEFAULT_PERIDOT_INPUT_POLL_S,
    get_peridot_input_wait_s,
    get_peridot_input_poll_s,
)

try:
    from wepppy.query_engine import update_catalog_entry as _update_catalog_entry
except ImportError:  # pragma: no cover - optional catalog support
    _update_catalog_entry = None

LOGGER = logging.getLogger(__name__)
_MANIFEST_FILE_HEADING = '## File Manifest'
_MANIFEST_SCHEMA_HEADING = '## Tabular Schema Summary'

# Default CPU count for peridot processes, can be overridden via PERIDOT_CPU env var
_DEFAULT_PERIDOT_CPU = '24'


def _get_peridot_ncpu() -> str:
    """Get the number of CPUs to use for peridot processes."""
    return os.environ.get('PERIDOT_CPU', _DEFAULT_PERIDOT_CPU)


def _wait_for_file(
    path: str,
    *,
    timeout_s: float,
    poll_s: float = DEFAULT_PERIDOT_INPUT_POLL_S,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Wait for ``path`` to exist before proceeding.

    This is a defensive guard for cases where upstream tools create files
    asynchronously and downstream jobs begin before writes are visible.
    """
    if _exists(path):
        return

    if timeout_s <= 0:
        raise FileNotFoundError(f'Expected file {path} to exist')

    if logger is not None:
        logger.info('Waiting up to %.2fs for %s', timeout_s, path)

    deadline = time.monotonic() + timeout_s
    while True:
        if _exists(path):
            return
        if time.monotonic() >= deadline:
            raise FileNotFoundError(f'Expected file {path} to be available within {timeout_s:.2f}s')
        time.sleep(poll_s)


def _detect_manifest_format(path: Path) -> str:
    ext = path.suffix.lower().lstrip('.')
    if ext in {'parquet', 'csv', 'geojson', 'json', 'txt'}:
        return ext
    if ext in {'slp', 'slps'}:
        return 'slp'
    if ext == 'md':
        return 'markdown'
    return ext or 'file'


def _replace_markdown_section(markdown: str, heading: str, replacement: str) -> str:
    pattern = re.compile(rf'(?ms)^{re.escape(heading)}\n\n.*?(?=^## |\Z)')
    normalized = replacement.rstrip('\n') + '\n\n'
    if pattern.search(markdown):
        return pattern.sub(normalized, markdown, count=1)
    return f'{markdown.rstrip()}\n\n{normalized}'


def _build_manifest_file_section(
    watershed_dir: Path,
    tabular_rows: dict[str, int],
    readme_size: Optional[int],
) -> str:
    rows = []
    slope_bundle_rows: dict[str, dict[str, int]] = {}
    for path in sorted(watershed_dir.rglob('*')):
        if not path.is_file():
            continue
        rel = f'watershed/{path.relative_to(watershed_dir).as_posix()}'
        if rel == 'watershed/README.md':
            continue
        if rel.startswith('watershed/slope_files/hillslopes/'):
            entry = slope_bundle_rows.setdefault(
                'watershed/slope_files/hillslopes/*',
                {'size': 0, 'files': 0},
            )
            entry['size'] += path.stat().st_size
            entry['files'] += 1
            continue
        if rel.startswith('watershed/slope_files/flowpaths/'):
            entry = slope_bundle_rows.setdefault(
                'watershed/slope_files/flowpaths/*',
                {'size': 0, 'files': 0},
            )
            entry['size'] += path.stat().st_size
            entry['files'] += 1
            continue
        fmt = _detect_manifest_format(path)
        size = path.stat().st_size
        if rel in tabular_rows:
            tabular_row_count = str(tabular_rows[rel])
        elif fmt in {'parquet', 'csv'}:
            tabular_row_count = 'unknown'
        else:
            tabular_row_count = '-'
        rows.append((rel, fmt, size, tabular_row_count))

    for rel, aggregate in slope_bundle_rows.items():
        rows.append((rel, 'slp bundle', aggregate['size'], f"{aggregate['files']} files"))
    rows.sort(key=lambda item: item[0])

    readme_size_display = str(readme_size) if readme_size is not None else 'pending'
    lines = [
        _MANIFEST_FILE_HEADING,
        '',
        'Refreshed by WEPPpy post-processing to reflect final parquet outputs.',
        '',
        '| Path | Format | Size (bytes) | Rows |',
        '| --- | --- | ---: | ---: |',
    ]
    for rel, fmt, size, row_count in rows:
        lines.append(f'| {rel} | {fmt} | {size} | {row_count} |')
    lines.append(f'| watershed/README.md | markdown | {readme_size_display} | - |')
    return '\n'.join(lines)


def _build_manifest_schema_section(
    tabular_rows: dict[str, int],
    tabular_schemas: dict[str, list[tuple[str, str]]],
) -> str:
    lines = [
        _MANIFEST_SCHEMA_HEADING,
        '',
        'Canonical downstream contract uses parquet tables. Compatibility CSV files may omit derived columns.',
        '',
    ]
    if not tabular_schemas:
        lines.append('No tabular outputs were recorded.')
        return '\n'.join(lines)

    for rel in sorted(tabular_schemas):
        lines.append(f'### `{rel}` (format: parquet, rows: {tabular_rows[rel]})')
        lines.append('')
        lines.append('| Column | Type |')
        lines.append('| --- | --- |')
        for column_name, dtype_name in tabular_schemas[rel]:
            lines.append(f'| {column_name} | {dtype_name} |')
        lines.append('')
    return '\n'.join(lines)


def _refresh_watershed_readme(
    watershed_dir: Path,
    tabular_frames: dict[str, pd.DataFrame],
) -> None:
    readme_path = watershed_dir / 'README.md'
    if not readme_path.exists():
        return

    base_markdown = readme_path.read_text(encoding='utf-8')
    tabular_rows: dict[str, int] = {}
    tabular_schemas: dict[str, list[tuple[str, str]]] = {}
    for rel_path, frame in tabular_frames.items():
        tabular_rows[rel_path] = len(frame.index)
        tabular_schemas[rel_path] = [
            (column_name, str(dtype).lower())
            for column_name, dtype in frame.dtypes.items()
        ]

    readme_size: Optional[int] = None
    for _ in range(3):
        file_section = _build_manifest_file_section(
            watershed_dir,
            tabular_rows=tabular_rows,
            readme_size=readme_size,
        )
        schema_section = _build_manifest_schema_section(tabular_rows, tabular_schemas)
        refreshed = _replace_markdown_section(
            base_markdown,
            _MANIFEST_FILE_HEADING,
            file_section,
        )
        refreshed = _replace_markdown_section(
            refreshed,
            _MANIFEST_SCHEMA_HEADING,
            schema_section,
        )
        readme_path.write_text(refreshed, encoding='utf-8')
        observed_size = readme_path.stat().st_size
        if readme_size == observed_size:
            return
        readme_size = observed_size
        base_markdown = refreshed


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
    skip_flowpaths: bool = True,
    verbose: bool = True
):
    _wait_for_file(
        _join(wd, 'dem/topaz/SUBWTA.ARC'),
        timeout_s=get_peridot_input_wait_s(),
        poll_s=get_peridot_input_poll_s(),
        logger=LOGGER,
    )

    cmd = [_get_bin(), wd, '--ncpu', _get_peridot_ncpu()]

    if clip_hillslopes:
        assert clip_hillslope_length > 0.0
        cmd += ['--clip-hillslopes', '--clip-hillslope-length', str(clip_hillslope_length)]

    if bieger2015_widths:
        cmd += ['--bieger2015-widths']

    if skip_flowpaths:
        cmd += ['--skip-flowpaths']

    if verbose:
        print(' '.join(cmd))

    with open(_join(wd, '_peridot.log'), 'w') as _log:
        p = Popen(cmd, stdout=_log, stderr=_log)
        p.wait()

def run_peridot_wbt_abstract_watershed(
    wd: str,
    clip_hillslopes: bool = True,
    clip_hillslope_length: float = 300.0,
    bieger2015_widths: bool = False,
    skip_flowpaths: bool = True,
    verbose: bool = True,
    representative_flowpath: bool = False
):
    """
    Run the Peridot abstract watershed tool using WhiteboxTools.

    Parameters:
        wd (str): Working directory where the Topaz data is located.
        clip_hillslopes (bool): Whether to clip hillslopes.
        clip_hillslope_length (float): Length to clip hillslopes.
        bieger2015_widths (bool): Whether to use Bieger 2015 widths.
        skip_flowpaths (bool): If True, skip flowpath generation to reduce memory usage.
        verbose (bool): If True, print command details.
        representative_flowpath (bool): If True, use a single representative flowpath per hillslope.
    """
    _wait_for_file(
        _join(wd, 'dem/wbt/subwta.tif'),
        timeout_s=get_peridot_input_wait_s(),
        poll_s=get_peridot_input_poll_s(),
        logger=LOGGER,
    )

    cmd = [_get_wbt_bin(), wd, '--ncpu', _get_peridot_ncpu()]

    if clip_hillslopes:
        assert clip_hillslope_length > 0.0
        cmd += ['--clip-hillslopes', '--clip-hillslope-length', str(clip_hillslope_length)]

    if bieger2015_widths:
        cmd += ['--bieger2015-widths']

    if representative_flowpath:
        cmd += ['--representative-flowpath']
    elif skip_flowpaths:
        cmd += ['--skip-flowpaths']

    if verbose:
        print(' '.join(cmd))

    with open(_join(wd, '_peridot.log'), 'w') as _log:
        p = Popen(cmd, stdout=_log, stderr=_log)
        p.wait()


def post_abstract_watershed(wd: str, verbose: bool = True):
    """
    Post-process the output of the Peridot abstract watershed tool.

    calculate and return ws_cenroid and ws_area
    """

    from wepppy.topo.watershed_abstraction import WeppTopTranslator

    watershed_dir = Path(wd) / "watershed"
    hill_df_raw, hill_source = _load_watershed_table(watershed_dir, "hillslopes")
    chn_df_raw, chn_source = _load_watershed_table(watershed_dir, "channels")

    if hill_df_raw is None:
        raise FileNotFoundError(
            "Missing watershed hillslope table; expected watershed/hillslopes.parquet "
            "or watershed/hillslopes.csv"
        )
    if chn_df_raw is None:
        raise FileNotFoundError(
            "Missing watershed channel table; expected watershed/channels.parquet "
            "or watershed/channels.csv"
        )

    if hill_source is not None and hill_source.suffix.lower() == ".csv":
        LOGGER.warning(
            "Legacy fallback path active: using watershed/hillslopes.csv because "
            "watershed/hillslopes.parquet is missing for %s",
            wd,
        )
    if chn_source is not None and chn_source.suffix.lower() == ".csv":
        LOGGER.warning(
            "Legacy fallback path active: using watershed/channels.csv because "
            "watershed/channels.parquet is missing for %s",
            wd,
        )

    hill_df = hill_df_raw.copy()
    chn_df = chn_df_raw.copy()

    hill_df['topaz_id'] = _extract_int32_column(hill_df, 'topaz_id', ('TopazID',))
    chn_df['topaz_id'] = _extract_int32_column(chn_df, 'topaz_id', ('TopazID',))

    sub_ids = sorted([int(x) for x in hill_df['topaz_id']])
    chn_ids = sorted([int(x) for x in  chn_df['topaz_id']])

    translator = WeppTopTranslator(sub_ids, chn_ids)
    get_wepp_id = lambda topaz_id: translator.wepp(topaz_id)
    get_chn_enum = lambda topaz_id: translator.chn_enum(top=topaz_id)

    hill_df['wepp_id'] = hill_df['topaz_id'].apply(lambda top: get_wepp_id(int(top))).astype('Int32')

    hill_df.to_parquet(_join(wd, 'watershed/hillslopes.parquet'), index=False)
    sub_area = float(hill_df['area'].sum())
    lngs = hill_df['centroid_lon'].to_numpy()
    lats = hill_df['centroid_lat'].to_numpy()

    chn_df['wepp_id'] = chn_df['topaz_id'].apply(lambda top: get_wepp_id(int(top))).astype('Int32')
    chn_df['chn_enum'] = chn_df['topaz_id'].apply(lambda top: get_chn_enum(int(top))).astype('Int32')

    chn_df.to_parquet(_join(wd, 'watershed/channels.parquet'), index=False)
    chn_area = float(chn_df['area'].sum())
    lngs = np.concatenate((lngs, chn_df['centroid_lon'].to_numpy()))
    lats = np.concatenate((lats, chn_df['centroid_lat'].to_numpy()))

    # Handle flowpaths metadata. This may be absent when skip-flowpaths mode is enabled.
    flowpaths_parquet = _join(wd, 'watershed/flowpaths.parquet')
    fps_df_raw, fps_source = _load_watershed_table(watershed_dir, "flowpaths")
    fps_df = None
    if fps_df_raw is not None:
        if fps_source is not None and fps_source.suffix.lower() == ".csv":
            LOGGER.warning(
                "Legacy fallback path active: using watershed/flowpaths.csv because "
                "watershed/flowpaths.parquet is missing for %s",
                wd,
            )
        fps_df = fps_df_raw.copy()
        fps_df['topaz_id'] = _extract_int32_column(fps_df, 'topaz_id', ('TopazID',))
        fps_df['fp_id'] = _extract_int32_column(fps_df, 'fp_id', ())
        fps_df.to_parquet(flowpaths_parquet, index=False)

    _refresh_watershed_readme(
        watershed_dir,
        {
            'watershed/hillslopes.parquet': hill_df,
            'watershed/channels.parquet': chn_df,
            **(
                {'watershed/flowpaths.parquet': fps_df}
                if fps_df is not None
                else {}
            ),
        },
    )

    if _update_catalog_entry is not None:
        try:
            _update_catalog_entry(wd, "watershed/hillslopes.parquet")
            _update_catalog_entry(wd, "watershed/channels.parquet")
            _update_catalog_entry(wd, "watershed/flowpaths.parquet")
            _update_catalog_entry(wd, "watershed")
        except Exception:  # broad-except: catalog refresh best effort  # pragma: no cover
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

    cmd = [_get_wbt_sub_field_bin(), wd, '--ncpu', _get_peridot_ncpu()]

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
        except Exception:  # broad-except: catalog refresh best effort  # pragma: no cover
            LOGGER.warning("Failed to refresh catalog for ag_fields/sub_fields in %s", wd, exc_info=True)

    return len(field_df), len(fps_df)


def _load_watershed_table(watershed_dir, stem: str):
    csv_path = Path(watershed_dir, f"{stem}.csv")
    parquet_path = Path(watershed_dir, f"{stem}.parquet")
    if parquet_path.exists():
        return pd.read_parquet(parquet_path), parquet_path
    if csv_path.exists():
        return pd.read_csv(csv_path), csv_path
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
    canonical_candidates = [
        watershed_dir / "hillslopes.parquet",
        watershed_dir / "channels.parquet",
        watershed_dir / "flowpaths.parquet",
    ]
    if not watershed_dir.exists() and not any(path.exists() for path in canonical_candidates):
        if verbose:
            print(f"[migrate_watershed_outputs] Skipping {wd}: watershed directory missing")
        return False

    watershed = Watershed.getInstance(wd)
    if not (watershed.delineation_backend_is_topaz or watershed.delineation_backend_is_wbt):
        if verbose:
            print(f"[migrate_watershed_outputs] Skipping {wd}: not a Peridot abstraction backend")
        return False

    hill_df_raw, _hill_source = _load_watershed_table(watershed_dir, "hillslopes")
    chn_df_raw, _chn_source = _load_watershed_table(watershed_dir, "channels")
    fp_df_raw, _fp_source = _load_watershed_table(watershed_dir, "flowpaths")

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

    if fp_df_raw is not None:
        fp_df = fp_df_raw.copy()
        fp_df["topaz_id"] = _extract_int32_column(fp_df, "topaz_id", ("TopazID",))
        fp_df["fp_id"] = _extract_int32_column(fp_df, "fp_id", (), allow_missing=False)

        fp_target = watershed_dir / "flowpaths.parquet"
        fp_df.to_parquet(fp_target, index=False)
        modified = True

    if remove_csv:
        for legacy_name in ("hillslopes.csv", "channels.csv", "flowpaths.csv"):
            legacy_path = watershed_dir / legacy_name
            try:
                legacy_path.unlink()
            except FileNotFoundError:
                pass

    if modified and _update_catalog_entry is not None:
        try:
            _update_catalog_entry(wd, "watershed/hillslopes.parquet")
            if (watershed_dir / "channels.parquet").exists():
                _update_catalog_entry(wd, "watershed/channels.parquet")
            if (watershed_dir / "flowpaths.parquet").exists():
                _update_catalog_entry(wd, "watershed/flowpaths.parquet")
            _update_catalog_entry(wd, "watershed")
        except Exception:  # broad-except: catalog refresh best effort  # pragma: no cover
            LOGGER.warning("Failed to refresh catalog for watershed outputs in %s", wd, exc_info=True)

    if verbose:
        if modified:
            print(f"[migrate_watershed_outputs] Standardized watershed tables for {wd}")
        else:
            print(f"[migrate_watershed_outputs] No changes required for {wd}")

    return modified
