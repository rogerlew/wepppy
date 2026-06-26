# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""Disturbed land-use NoDb controller.

The Disturbed mod lets users parameterize wildfire, logging, and other acute
disturbance scenarios for WEPP runs. It ingests disturbance lookup tables,
reprojects geospatial rasters into the watershed frame, and orchestrates the
creation of WEPP-ready management, soil, and slope artifacts for affected
subcatchments.

Key Responsibilities:
    - Parse CSV lookup tables describing disturbance-to-soil/land-use mappings.
    - Reproject disturbance rasters into the watershed DEM grid using RasterIO.
    - Synthesize WEPP soil files (multi-OFE) and management records for each
      impacted hillslope.
    - Emit progress events via Redis so the UI can track long-running jobs.

Typical Usage:
    >>> from wepppy.nodb.mods import Disturbed
    >>> disturbed = Disturbed.getInstance('/runs/example')
    >>> with disturbed.locked():
    ...     disturbed.apply_disturbance('fire_2024.tif')
    ...     disturbed.dump_and_unlock()

See also:
    - docs/ui-docs/control-ui-styling/sbs_controls_behavior.md - Frontend SBS control architecture
    - wepppy/weppcloud/controllers_js/README.md - Controller system documentation
"""

import os
import ast
import csv
import json
import hashlib
import shutil
import tempfile
import inspect
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from subprocess import Popen, PIPE
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
from copy import deepcopy
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, wait
from concurrent.futures.process import BrokenProcessPool
from typing import Optional, Dict, List, Tuple, Any, Union, Sequence

import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
import math
import numpy as np
from osgeo import gdal

from deprecated import deprecated

from wepppy.all_your_base import NCPU, isint, isfloat
from wepppy.all_your_base.geo import wgs84_proj4, read_raster, haversine, raster_stacker, validate_srs
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import simple_texture, WeppSoilUtil, SoilMultipleOfeSynth

from wepppy.nodb.core import (
    Landuse,
    Ron,
    Watershed,
)
from wepppy.nodb.core.management_overrides import is_unburned_forest_disturbed_class
from ...redis_prep import RedisPrep, TaskEnum
from ...base import NoDbBase, TriggerEvents, createProcessPoolExecutor, nodb_setter
from ..baer.sbs_map import SoilBurnSeverityMap
from .. import MODS_DIR, EXTENDED_MODS_DATA

from wepppyo3.raster_characteristics import count_intersecting_raster_key_pairs

__all__ = [
    'disturbed_class_aliases',
    'TREATMENT_SUFFIXES',
    'lookup_disturbed_class',
    'read_disturbed_land_soil_lookup',
    'get_disturbed_land_soil_lookup_snapshot',
    'get_disturbed_land_soil_lookup_sha256',
    'migrate_land_soil_lookup',
    'write_disturbed_land_soil_lookup',
    'DisturbedNoDbLockedException',
    'InvalidProjection',
    'Disturbed',
]

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')
_logger = logging.getLogger(__name__)


def _resolve_external_mods_path(path: Optional[str]) -> Optional[str]:
    """Expand MODS_DIR/EXTENDED_MODS_DATA placeholders for fallback callers."""
    if not path:
        return path
    return (
        path.replace('MODS_DIR', MODS_DIR)
        .replace('EXTENDED_MODS_DATA', EXTENDED_MODS_DATA)
    )


disturbed_class_aliases: Dict[str, str] = {
    'forest prescribed fire': 'prescribed fire',
    'forest high sev fire': 'high sev fire',
    'forest moderate sev fire': 'moderate sev fire',
    'forest low sev fire': 'low sev fire',
}

# Treatment suffixes that should be stripped when looking up base disturbed class
TREATMENT_SUFFIXES = ('-mulch_15', '-mulch_30', '-mulch_60', '-thinning', '-prescribed_fire')
LOOKUP_KEY_FIELDS: Tuple[str, str] = ('luse', 'stext')
LOOKUP_FALLBACK_KEY_FIELDS: Tuple[str, str] = ('disturbed_class', 'texid')
LOOKUP_REQUIRED_COLUMNS: Tuple[str, ...] = (
    'pmet_kcb',
    'pmet_rawp',
    'rdmax',
    'xmxlai',
    'keffflag',
    'lkeff',
)
LOOKUP_REQUIRED_KEYS: Tuple[Tuple[str, str], ...] = (
    ('forest moderate sev fire', 'loam'),
)


def lookup_disturbed_class(disturbed_class: Optional[str]) -> Optional[str]:
    """
    Extract the base disturbed class from a treatment-modified class.
    
    Treatment scenarios append suffixes like '-mulch_15' to the base disturbed class.
    For soil parameter lookups, we need the base class (e.g., 'forest moderate sev fire')
    because the soil erodibility is determined by fire severity, not treatment type.
    
    Examples:
        'forest moderate sev fire-mulch_15' -> 'forest moderate sev fire'
        'shrub high sev fire-mulch_30' -> 'shrub high sev fire'
        'forest high sev fire' -> 'forest high sev fire'
        None -> None
    """
    if disturbed_class is None:
        return None
    
    for suffix in TREATMENT_SUFFIXES:
        if disturbed_class.endswith(suffix):
            return disturbed_class[:-len(suffix)]
    
    return disturbed_class


def _read_lookup_rows(fname: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    with open(fname) as fp:
        reader = csv.DictReader(fp)
        fieldnames = list(reader.fieldnames or [])
        rows: List[Dict[str, Any]] = []
        for row in reader:
            rows.append({field: row.get(field, '') for field in fieldnames})
    return fieldnames, rows


def _lookup_row_key(row: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    luse = row.get('luse') or row.get('disturbed_class')
    stext = row.get('stext') or row.get('texid')
    if luse is None or stext is None:
        return None
    luse_str = str(luse).strip()
    stext_str = str(stext).strip()
    if not luse_str or not stext_str:
        return None
    return luse_str, stext_str


def _atomic_write_lookup_rows(fname: str, fieldnames: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
    if not fieldnames:
        raise ValueError('lookup fieldnames are empty')

    os.makedirs(os.path.dirname(fname), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix='disturbed_land_soil_lookup.',
        suffix='.csv',
        dir=os.path.dirname(fname),
    )
    os.close(fd)

    try:
        with open(tmp_path, 'w') as fp:
            writer = csv.DictWriter(fp, list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, '') for field in fieldnames})

        backup_fn = f'{fname}.bak'
        if _exists(fname):
            shutil.copyfile(fname, backup_fn)
        os.replace(tmp_path, fname)
    finally:
        if _exists(tmp_path):
            os.remove(tmp_path)


def _lookup_file_snapshot(fname: str) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {'path': fname, 'exists': _exists(fname)}
    if not snapshot['exists']:
        return snapshot

    try:
        stat = os.stat(fname)
        snapshot['size_bytes'] = stat.st_size
        snapshot['mtime_epoch'] = stat.st_mtime
    except OSError:
        return snapshot

    digest = hashlib.sha256()
    try:
        with open(fname, 'rb') as fp:
            for chunk in iter(lambda: fp.read(65536), b''):
                digest.update(chunk)
        snapshot['sha256'] = digest.hexdigest()
    except OSError:
        snapshot['sha256'] = None

    try:
        fieldnames, rows = _read_lookup_rows(fname)
        snapshot['columns'] = len(fieldnames)
        snapshot['rows'] = len(rows)
    except (OSError, csv.Error, UnicodeError):
        pass

    return snapshot


def _parse_rgb_key(rgb: str) -> Tuple[int, int, int]:
    """Convert persisted RGB keys like ``"255_0_0"`` into numeric tuples."""
    return tuple(int(part) for part in rgb.split('_'))


def _lookup_audit_path(lookup_path: str) -> str:
    return _join(os.path.dirname(lookup_path), 'disturbed_lookup_audit.jsonl')


def get_disturbed_land_soil_lookup_snapshot(fname: str) -> Dict[str, Any]:
    """Return current lookup file fingerprint metadata."""
    return _lookup_file_snapshot(fname)


def get_disturbed_land_soil_lookup_sha256(fname: str) -> Optional[str]:
    """Return current lookup SHA-256 fingerprint when readable."""
    snapshot = _lookup_file_snapshot(fname)
    value = snapshot.get('sha256')
    return value if isinstance(value, str) and value else None


def _emit_lookup_audit(
    event: str,
    lookup_path: str,
    *,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'event': event,
        'lookup_path': lookup_path,
        'before': before,
        'after': after,
        'details': details or {},
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    _logger.info('disturbed_lookup_audit %s', serialized)

    audit_fn = _lookup_audit_path(lookup_path)
    try:
        os.makedirs(os.path.dirname(audit_fn), exist_ok=True)
        with open(audit_fn, 'a') as fp:
            fp.write(serialized)
            fp.write('\n')
    except OSError as exc:
        _logger.warning(
            'disturbed_lookup_audit_write_failed path=%s err=%s',
            audit_fn,
            exc,
        )


def _normalize_lookup_payload_row(
    row: Union[List[Any], Tuple[Any, ...], Dict[str, Any]],
    fieldnames: Sequence[str],
    index: int,
) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}

    if isinstance(row, (list, tuple)):
        if len(row) != len(fieldnames):
            raise ValueError(
                f'row {index} has {len(row)} columns; expected {len(fieldnames)}'
            )
        normalized = {field: value for field, value in zip(fieldnames, row)}
    elif isinstance(row, dict):
        missing_fields: List[str] = []
        for field in fieldnames:
            if field in row:
                continue
            if field == 'luse' and str(row.get('disturbed_class', '')).strip():
                continue
            if field == 'stext' and str(row.get('texid', '')).strip():
                continue
            missing_fields.append(field)
        if missing_fields:
            preview = ', '.join(missing_fields[:5])
            raise ValueError(f'row {index} is missing columns: {preview}')
        normalized = {field: row.get(field, '') for field in fieldnames}
        if 'luse' in fieldnames and not normalized.get('luse'):
            normalized['luse'] = row.get('disturbed_class', '')
        if 'stext' in fieldnames and not normalized.get('stext'):
            normalized['stext'] = row.get('texid', '')
    else:
        raise ValueError(f'row {index} must be a list or mapping')

    key = _lookup_row_key(normalized)
    if key is None:
        raise ValueError(f'row {index} must include non-empty luse/stext key values')

    if 'luse' in fieldnames:
        normalized['luse'] = key[0]
    if 'stext' in fieldnames:
        normalized['stext'] = key[1]
    return normalized


def read_disturbed_land_soil_lookup(fname: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    d = {}

    with open(fname) as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            disturbed_class = str(row.get('luse') or row.get('disturbed_class') or '').strip()
            texid = str(row.get('stext') or row.get('texid') or '').strip()

            for k in row:
                v = row[k]
                if isinstance(v, str):
                    if v.lower().startswith('none'):
                        row[k] = None

            if texid != '' and disturbed_class != '':

                if texid == 'all':
                    d[('clay loam', disturbed_class)] = row
                    d[('loam', disturbed_class)] = row
                    d[('sand loam', disturbed_class)] = row
                    d[('silt loam', disturbed_class)] = row
                else:
                    d[(texid, disturbed_class)] = row

            if disturbed_class in disturbed_class_aliases:
                alias = disturbed_class_aliases[disturbed_class]
                if texid != '' and alias != '':
                    d[(texid, alias)] = row
    return d

def migrate_land_soil_lookup(
    src_fn: str, 
    target_fn: str, 
    pars: List[str], 
    defaults: Dict[str, Any]
) -> None:
    before_snapshot = _lookup_file_snapshot(target_fn)
    src = read_disturbed_land_soil_lookup(src_fn)
    target = read_disturbed_land_soil_lookup(target_fn)

    for k in src:
        if k not in target:
            target[k] = src[k]

    for par in pars:
        for k in target:
            if par in src[k]:
                v = src[k][par]
            else:
                v = defaults[par]
            target[k][par] = v

    fieldnames = list(target[k].keys())

    with open(target_fn, 'w') as fp:
        wtr = csv.DictWriter(fp, fieldnames)
        wtr.writeheader()

        for k, row in target.items():
            wtr.writerow(row)

    _emit_lookup_audit(
        'lookup.migrate',
        target_fn,
        before=before_snapshot,
        after=_lookup_file_snapshot(target_fn),
        details={
            'source_lookup': src_fn,
            'target_rows': len(target),
            'added_parameters': list(pars),
        },
    )


def write_disturbed_land_soil_lookup(
    fname: str,
    data: List[Union[List[Any], Tuple[Any, ...], Dict[str, Any]]],
) -> None:
    before_snapshot = _lookup_file_snapshot(fname)
    fieldnames, existing_rows = _read_lookup_rows(fname)
    if not fieldnames:
        raise ValueError('lookup file has no header row')
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError('rows payload must be a non-empty list')

    incoming_rows = [
        _normalize_lookup_payload_row(row, fieldnames, index=i)
        for i, row in enumerate(data, start=1)
    ]

    existing_keys = {
        key
        for row in existing_rows
        if (key := _lookup_row_key(row)) is not None
    }
    incoming_keys = {
        key
        for row in incoming_rows
        if (key := _lookup_row_key(row)) is not None
    }
    if existing_keys - incoming_keys:
        raise ValueError('rows payload is missing existing lookup rows; refresh and retry')

    seen_keys: set[Tuple[str, str]] = set()
    for i, row in enumerate(incoming_rows, start=1):
        key = _lookup_row_key(row)
        assert key is not None
        if key in seen_keys:
            raise ValueError(f'row {i} duplicates key values: {key[0]}/{key[1]}')
        seen_keys.add(key)

    _atomic_write_lookup_rows(fname, fieldnames, incoming_rows)
    _emit_lookup_audit(
        'lookup.write',
        fname,
        before=before_snapshot,
        after=_lookup_file_snapshot(fname),
        details={
            'incoming_rows': len(incoming_rows),
            'existing_rows': len(existing_rows),
        },
    )


def upgrade_disturbed_land_soil_lookup(
    target_fn: str,
    default_fn: str,
) -> bool:
    before_snapshot = _lookup_file_snapshot(target_fn)
    target_fieldnames, target_rows = _read_lookup_rows(target_fn)
    default_fieldnames, default_rows = _read_lookup_rows(default_fn)
    if not default_fieldnames:
        raise ValueError('default disturbed lookup has no header row')

    normalized_fieldnames = list(default_fieldnames)
    for field in target_fieldnames:
        if field not in normalized_fieldnames:
            normalized_fieldnames.append(field)

    default_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in default_rows:
        key = _lookup_row_key(row)
        if key is not None:
            default_by_key[key] = row

    changed = False
    normalized_rows: List[Dict[str, Any]] = []
    present_keys: set[Tuple[str, str]] = set()

    for row in target_rows:
        normalized = {field: row.get(field, '') for field in normalized_fieldnames}
        key = _lookup_row_key(normalized)
        if key is not None:
            if 'luse' in normalized_fieldnames and str(normalized.get('luse', '')).strip() != key[0]:
                normalized['luse'] = key[0]
                changed = True
            if 'stext' in normalized_fieldnames and str(normalized.get('stext', '')).strip() != key[1]:
                normalized['stext'] = key[1]
                changed = True
            present_keys.add(key)
            default_row = default_by_key.get(key, {})
            for field in LOOKUP_REQUIRED_COLUMNS:
                if field not in normalized_fieldnames:
                    continue
                if str(normalized.get(field, '')).strip() == '':
                    fallback = default_row.get(field, '')
                    if str(fallback).strip() != '':
                        normalized[field] = fallback
                        changed = True
        if normalized != row:
            changed = True
        normalized_rows.append(normalized)

    for row in default_rows:
        key = _lookup_row_key(row)
        if key is None or key in present_keys:
            continue
        normalized_rows.append({field: row.get(field, '') for field in normalized_fieldnames})
        present_keys.add(key)
        changed = True

    for required_key in LOOKUP_REQUIRED_KEYS:
        if required_key not in present_keys and required_key in default_by_key:
            row = default_by_key[required_key]
            normalized_rows.append({field: row.get(field, '') for field in normalized_fieldnames})
            present_keys.add(required_key)
            changed = True

    if target_fieldnames != normalized_fieldnames:
        changed = True

    if changed:
        _atomic_write_lookup_rows(target_fn, normalized_fieldnames, normalized_rows)
    _emit_lookup_audit(
        'lookup.schema_upgrade',
        target_fn,
        before=before_snapshot,
        after=_lookup_file_snapshot(target_fn),
        details={
            'changed': changed,
            'target_rows': len(target_rows),
            'normalized_rows': len(normalized_rows),
            'target_columns': len(target_fieldnames),
            'normalized_columns': len(normalized_fieldnames),
        },
    )
    return changed


def _build_disturbed_mofe_soil(task_args: Dict[str, Any]) -> Tuple[str, float]:
    """Build one disturbed MOFE soil file and return its key plus elapsed seconds."""

    started = time.time()
    replacements = task_args.get('replacements')
    replacement_values = dict(replacements) if isinstance(replacements, dict) else None

    soil_u = WeppSoilUtil(task_args['source_soil_path'])
    if task_args['sol_ver'] == 7778.0:
        new = soil_u.to_7778disturbed(
            replacement_values,
            h0_max_om=task_args.get('h0_max_om'),
            recompute_wp_fc_using_rosetta_on_bd_override=task_args[
                'recompute_wp_fc_using_rosetta_on_bd_override'
            ],
        )
    else:
        new = soil_u.to_over9000(
            replacement_values,
            h0_max_om=task_args.get('h0_max_om'),
            recompute_wp_fc_using_rosetta_on_bd_override=task_args[
                'recompute_wp_fc_using_rosetta_on_bd_override'
            ],
            version=task_args['sol_ver'],
        )

    new.write(task_args['output_path'])
    return task_args['disturbed_mukey'], round(time.time() - started, 3)


class DisturbedNoDbLockedException(Exception):
    pass


class InvalidProjection(Exception):
    """
    Map contains an invalid projection. Try reprojecting to UTM.
    """

    __name__ = 'Invalid Projection'


class Disturbed(NoDbBase):
    __name__ = 'Disturbed'
    LOOKUP_VARIANT_BASE = 'base'
    LOOKUP_VARIANT_EXTENDED = 'extended'

    filename = 'disturbed.nodb'

    def __init__(
        self, 
        wd: str, 
        cfg_fn: str, 
        run_group: Optional[str] = None, 
        group_name: Optional[str] = None
    ) -> None:
        super(Disturbed, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            os.mkdir(self.disturbed_dir)

            self._disturbed_fn = None
            self._bounds = None
            self._classes = None
            self._breaks = None
            self._counts = None
            self._nodata_vals = None
            self._is256 = None
            self._ct = None
            self._color_map = None
            self._color_coverage_pcts = None
            self._sbs_mode = 0
            self._uniform_severity = None
            self._active_lookup_variant = None

            self.reset_land_soil_lookup(reason='init')

            self.sbs_coverage = None
            self._h0_max_om = self.config_get_float('disturbed', 'h0_max_om')
            self._sol_ver = self.config_get_float('disturbed', 'sol_ver')

            self._fire_date = self.config_get_str('disturbed', 'fire_date')
            self._burn_shrubs = self.config_get_bool('disturbed', 'burn_shrubs', True)
            self._burn_grass = self.config_get_bool('disturbed', 'burn_grass', False)

    @property
    def burn_shrubs(self) -> bool:
        return getattr(self, '_burn_shrubs', True)

    def _set_burn_shrubs_value(self, value: bool) -> None:
        self._burn_shrubs = bool(value)
    
    @burn_shrubs.setter
    @nodb_setter
    def burn_shrubs(self, value: bool) -> None:
        self._set_burn_shrubs_value(value)

    @property
    def burn_grass(self) -> bool:
        return getattr(self, '_burn_grass', False)

    def _set_burn_grass_value(self, value: bool) -> None:
        self._burn_grass = bool(value)
    
    @burn_grass.setter
    @nodb_setter
    def burn_grass(self, value: bool) -> None:
        self._set_burn_grass_value(value)

    def apply_build_landuse_updates(
        self,
        *,
        burn_shrubs: Optional[bool] = None,
        burn_grass: Optional[bool] = None,
    ) -> None:
        """Apply build-landuse route updates in one lock scope."""

        if burn_shrubs is None and burn_grass is None:
            return

        with self.locked():
            if burn_shrubs is not None:
                self._set_burn_shrubs_value(burn_shrubs)
            if burn_grass is not None:
                self._set_burn_grass_value(burn_grass)

    @property
    def fire_date(self) -> Optional[str]:
        return getattr(self, "_fire_date", None)

    @fire_date.setter
    @nodb_setter
    def fire_date(self, value: str) -> None:
        self._fire_date = value

    @property
    def default_land_soil_lookup_fn(self) -> str:
        _lookup_path = self.config_get_path('disturbed', 'land_soil_lookup', None)
        if _lookup_path is None:
            _lookup_path = _join(_data_dir, 'disturbed_land_soil_lookup.csv')
        return _resolve_external_mods_path(_lookup_path)

    def reset_land_soil_lookup(self, reason: str = 'manual') -> None:
        _lookup = _join(self.disturbed_dir, 'disturbed_land_soil_lookup.csv')
        before_snapshot = _lookup_file_snapshot(_lookup)

        if _exists(_lookup):
            os.remove(_lookup)

        shutil.copyfile(self.default_land_soil_lookup_fn, _lookup)
        _emit_lookup_audit(
            'lookup.reset',
            _lookup,
            before=before_snapshot,
            after=_lookup_file_snapshot(_lookup),
            details={'reason': reason},
        )

    @property
    def disturbed_dir(self) -> str:
        return _join(self.wd, 'disturbed')

    baer_dir = disturbed_dir

    @property
    def disturbed_soils_dir(self) -> str:
        return _join(_data_dir, 'soils')

    @property
    def disturbed_fn(self) -> Optional[str]:
        return self._disturbed_fn

    @property
    def has_map(self) -> bool:
        return self._disturbed_fn is not None

    @property
    def is256(self) -> bool:
        return self._is256 is not None

    @property
    def ct(self) -> Optional[Any]:
        return getattr(self, '_ct', None)

    @property
    def bounds(self) -> Optional[List[List[float]]]:
        return self._bounds

    @property
    def classes(self) -> Optional[List[int]]:
        return self._classes

    @property
    def breaks(self) -> Optional[List[int]]:
        return self._breaks

    @property
    def h0_max_om(self) -> Optional[float]:
        return getattr(self, '_h0_max_om', None)

    @property
    def sol_ver(self) -> float:
        return getattr(self, '_sol_ver', 7778.0)

    @sol_ver.setter
    @nodb_setter
    def sol_ver(self, value: float) -> None:
        self._sol_ver = float(value)

    @property
    def nodata_vals(self) -> str:
        if self._nodata_vals is None:
            return ''

        return ', '.join(str(v) for v in self._nodata_vals)

    @property
    def disturbed_path(self) -> Optional[str]:
        if self._disturbed_fn is None:
            return None

        return _join(self.disturbed_dir, self._disturbed_fn)

    def _available_disturbed_path(self) -> Optional[str]:
        disturbed_path = self.disturbed_path
        if disturbed_path is None or _exists(disturbed_path):
            return disturbed_path

        sbs_4class_path = self.sbs_4class_path
        if _exists(sbs_4class_path):
            logger_warning = getattr(self.logger, "warning", None)
            if callable(logger_warning):
                logger_warning(
                    "Configured SBS source %s is missing; using %s",
                    disturbed_path,
                    sbs_4class_path,
                )
            return sbs_4class_path

        return disturbed_path

    def _sbs_map_args(
        self,
        disturbed_path: str,
    ) -> Tuple[
        Optional[Sequence[int | float]],
        Optional[List[int | float]],
        Optional[Dict[Tuple[int, int, int], str]],
    ]:
        if disturbed_path == self.sbs_4class_path:
            return None, None, None
        return self.breaks, self._nodata_vals, self.color_to_severity_map

    @property
    def sbs_mode(self) -> int:
        return int(getattr(self, '_sbs_mode', 0))

    @sbs_mode.setter
    @nodb_setter
    def sbs_mode(self, value: int) -> None:
        self._sbs_mode = int(value)

    @property
    def uniform_severity(self) -> Optional[int]:
        severity = getattr(self, '_uniform_severity', None)
        return None if severity is None else int(severity)

    @uniform_severity.setter
    @nodb_setter
    def uniform_severity(self, value: Optional[int]) -> None:
        self._uniform_severity = int(value) if value is not None else None

    @property
    def active_lookup_variant(self) -> str:
        raw_variant = getattr(self, '_active_lookup_variant', None)
        if isinstance(raw_variant, str):
            normalized = raw_variant.strip().lower()
            if normalized in {self.LOOKUP_VARIANT_BASE, self.LOOKUP_VARIANT_EXTENDED}:
                return normalized

        if _exists(self.extended_lookup_fn):
            return self.LOOKUP_VARIANT_EXTENDED
        return self.LOOKUP_VARIANT_BASE

    @active_lookup_variant.setter
    @nodb_setter
    def active_lookup_variant(self, value: str) -> None:
        normalized = str(value).strip().lower()
        if normalized not in {self.LOOKUP_VARIANT_BASE, self.LOOKUP_VARIANT_EXTENDED}:
            raise ValueError("lookup_variant must be one of {'base', 'extended'}")
        self._active_lookup_variant = normalized

    def build_uniform_sbs(self, value: int = 4) -> str:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}({value})')

        with self.timed('  Building uniform SBS raster'):
            sbs_fn = _join(self.disturbed_dir, 'uniform_sbs.tif')

            # Open the input raster file
            with rasterio.open(self.ron_instance.dem_fn) as src:
                # Read the input raster data as a numpy array
                dem = src.read(1)

                # Define the output raster metadata based on the input raster metadata
                out_meta = src.meta.copy()
                out_meta.update(dtype=rasterio.uint8, count=1, nodata=255)

                # Create the output raster data as a numpy array
                # Pixel values: 1=low, 2=moderate, 3=high
                # Color table maps these to standard SBS codes via ct_classify
                out_arr = np.full_like(dem, fill_value=value, dtype=rasterio.uint8)

                # Write the output raster data to a new geotiff file
                with rasterio.open(sbs_fn, 'w', **out_meta) as dst:
                    dst.write(out_arr, 1)

            # Open the written raster file with GDAL to set color table
            ds = gdal.Open(sbs_fn, gdal.GA_Update)
            band = ds.GetRasterBand(1)
            color_table = gdal.ColorTable()
            color_table.SetColorEntry(0, (0, 100, 0, 255))  # unburned
            color_table.SetColorEntry(1, (127, 255, 212, 255))  # low
            color_table.SetColorEntry(2, (255, 255, 0, 255))  # moderate
            color_table.SetColorEntry(3, (255, 0, 0, 255))  # high
            color_table.SetColorEntry(255, (255, 255, 255, 0))  # n/a
            band.SetColorTable(color_table)
            band = None  # Dereference to make sure all data is written
            ds = None  # Dereference to make sure all data is written

            try:
                with self.locked():
                    # Persist both state fields in one transaction to avoid
                    # split writes across independent setter dumps.
                    self._sbs_mode = 1
                    self._uniform_severity = int(value)
            except AttributeError:
                # Support detached test doubles that intentionally bypass NoDb wiring.
                self._sbs_mode = 1
                self._uniform_severity = int(value)

            return sbs_fn

    @property
    def sbs_4class_path(self) -> str:
        return _join(self.disturbed_dir, 'sbs_4class.tif')

    @property
    def disturbed_wgs(self) -> str:
        disturbed_path = self.disturbed_path
        return disturbed_path[:-4] + '.wgs.tif'

    @property
    def disturbed_rgb(self) -> str:
        return self.disturbed_wgs[:-4] + '.rgb.vrt'

    @property
    def disturbed_rgb_png(self) -> str:
        return _join(self.disturbed_dir, 'baer.wgs.rgba.png')

    baer_rgb_png = disturbed_rgb_png

    @property
    def disturbed_cropped(self) -> str:
        return _join(self.disturbed_dir, 'baer.cropped.tif')

    @property
    def legend(self) -> List[Tuple[int, str, str]]:
        keys = [130, 131, 132, 133]

        descs = ['No Burn',
                'Low Severity Burn',
                'Moderate Severity Burn',
                'High Severity Burn']

        colors = ['#00734A', '#4DE600', '#FFFF00', '#FF0000']

        return list(zip(keys, descs, colors))

    @property
    def sbs_wgs_n(self) -> int:
        """
        number of pixels in the WGS projected SBS
        """
        return sum(self._counts.values())

    @property
    def sbs_wgs_area_ha(self) -> float:
        """
        area of the WGS projected SBS in ha
        """
        [[sw_y, sw_x], [ne_y, ne_x]] = self.bounds
        nw_y, nw_x = ne_y, sw_x

        width = haversine((nw_x, nw_y), (ne_x, ne_y)) * 1000
        height = haversine((nw_x, nw_y), (sw_x, sw_y)) * 1000
        return width * height * 0.0001

    @property
    def sbs_class_pcts(self) -> Dict[str, float]:
        """
        dictionary with burn class keys percentages of cover of the WGS projected SBS
        """
        counts = self._counts
        pcts = {}
        tot_px = counts.get('Low Severity Burn', 0) + \
                 counts.get('Moderate Severity Burn', 0) + \
                 counts.get('High Severity Burn', 0)

        for k in counts:
            if tot_px == 0:
                pcts[k] = 0.0
            else:
                pcts[k] = 100.0 * counts[k] / tot_px

        return pcts

    @property
    def sbs_class_areas(self) -> Dict[str, float]:
        """
        dictionary with burn class keys and areas (ha) of the WGS projected SBS
        """
        ha__px = self.sbs_wgs_area_ha / self.sbs_wgs_n
        counts = self._counts
        areas = {}

        for k in counts:
            areas[k] = counts[k] * ha__px 

        return areas

    @property
    def class_map(self) -> Dict[str, str]:
        disturbed_path = self._available_disturbed_path()
        if disturbed_path is None:
            raise FileNotFoundError("No SBS map is configured")

        breaks, nodata_vals, color_map = self._sbs_map_args(disturbed_path)
        sbs = SoilBurnSeverityMap(
            disturbed_path,
            breaks=breaks,
            nodata_vals=nodata_vals,
            color_map=color_map,
        )
        return sbs.class_map

    def modify_burn_class(
        self, 
        breaks: List[int], 
        nodata_vals: Optional[Union[str, List[int]]]
    ) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(breaks={breaks}, nodata_vals={nodata_vals})')

        assert len(breaks) == 4
        assert breaks[0] <= breaks[1]
        assert breaks[1] <= breaks[2]
        assert breaks[2] <= breaks[3]

        if nodata_vals is not None:
            if str(nodata_vals).strip() != '':
                nodata_vals = ast.literal_eval('[{}]'.format(nodata_vals))
                assert all(isint(v) for v in nodata_vals)

        self.validate(self.disturbed_path, breaks, nodata_vals)

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.landuse_map)
            prep.timestamp(TaskEnum.init_sbs_map)
            prep.has_sbs = True
        except FileNotFoundError:
            pass

    def modify_color_map(self, color_map: Dict[str, str]) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(color_map={color_map})')

        self.validate(self.disturbed_path, color_map=color_map)

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.landuse_map)
            prep.timestamp(TaskEnum.init_sbs_map)
            prep.has_sbs = True
        except FileNotFoundError:
            pass

    @property
    def color_to_severity_map(self) -> Optional[Dict[Tuple[int, int, int], str]]:
        if getattr(self, '_ct', None) is None:
            return None

        color_map = getattr(self, '_color_map', None)

        if color_map is None:
            self.validate(self.disturbed_path, self.breaks, self._nodata_vals)
            color_map = getattr(self, '_color_map', None)

        return {_parse_rgb_key(rgb): v for rgb, v in color_map.items()}

    @property
    def color_coverage_pcts(self) -> Dict[Tuple[int, int, int], float]:
        if getattr(self, '_ct', None) is None:
            return {}

        coverage_map = getattr(self, '_color_coverage_pcts', None)
        if coverage_map is None:
            self.validate(self.disturbed_path, self.breaks, self._nodata_vals)
            coverage_map = getattr(self, '_color_coverage_pcts', None)

        if coverage_map is None:
            return {}

        return {_parse_rgb_key(rgb): float(v) for rgb, v in coverage_map.items()}

    def remove_sbs(self) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        with self.locked():
            # Clearing SBS is a metadata transition; the source raster may be
            # reused by OMNI sibling scenarios or fork audits.
            self._disturbed_fn = None
            self._nodata_vals = None
            self._bounds = None
            self._is256 = None
            self._classes = None
            self._counts = None
            self._breaks = None
            self._ct = None
            self._color_map = None
            self._color_coverage_pcts = None
            self._sbs_mode = 0
            self._uniform_severity = None
            self.sbs_coverage = None

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.landuse_map)
            prep.has_sbs = False
        except FileNotFoundError:
            pass

    def validate(
        self, 
        fn: str, 
        breaks: Optional[List[int]] = None, 
        nodata_vals: Optional[Union[List[int], Tuple[int, ...]]] = None, 
        color_map: Optional[Dict[str, str]] = None,
        *, 
        mode: Optional[int] = None,
        uniform_severity: Optional[int] = None
    ) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(fn={fn}, breaks={breaks}, nodata_vals={nodata_vals}, color_map={color_map}, mode={mode}, uniform_severity={uniform_severity})')

        assert nodata_vals is None or isinstance(nodata_vals, (list, tuple)), nodata_vals
        assert not isinstance(nodata_vals, str), nodata_vals

        with self.locked():
            self._disturbed_fn = fn
            self._nodata_vals = nodata_vals
            disturbed_path = self.disturbed_path
            assert _exists(disturbed_path), disturbed_path

            if not validate_srs(disturbed_path):
                raise InvalidProjection("Map contains an invalid projection. Try reprojecting to UTM.")

            with self.timed('  Validating SBS raster and exporting maps'):
                sbs = SoilBurnSeverityMap(disturbed_path, breaks=breaks, nodata_vals=nodata_vals, color_map=color_map)

                self._bounds = sbs.export_wgs_map(self.disturbed_wgs)
                sbs.export_rgb_map(self.disturbed_wgs, self.disturbed_rgb, self.disturbed_rgb_png)
                sbs_4class_path = self.sbs_4class_path
                if _exists(sbs_4class_path):
                    os.remove(sbs_4class_path)
                sbs.export_4class_map(sbs_4class_path)

            self._ct = sbs.ct
            self._is256 = sbs.is256
            self._classes = sorted([int(x) for x in sbs.classes])
            self._counts = sbs.burn_class_counts
            if sbs.color_map is None:
                self._color_map = None
                self._color_coverage_pcts = None
            else:
                self._color_map = {'_'.join(str(x) for x in rgb): v for rgb, v in sbs.color_map.items()}
                self._color_coverage_pcts = {
                    '_'.join(str(x) for x in rgb): pct
                    for rgb, pct in sbs.color_coverage_pcts.items()
                }
            self._breaks = sbs.breaks
            self._nodata_vals = sbs.nodata_vals
            if mode is not None:
                self._sbs_mode = int(mode)
                if mode == 0 and uniform_severity is None:
                    self._uniform_severity = None
            if uniform_severity is not None:
                self._uniform_severity = int(uniform_severity)

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.landuse_map)
            prep.timestamp(TaskEnum.init_sbs_map)
            prep.has_sbs = True
        except FileNotFoundError:
            pass

    def on(self, evt: TriggerEvents) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}({evt})')

        multi_ofe = self.multi_ofe

        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            self.logger.info(f'  Routing to LANDUSE_DOMLC_COMPLETE')
            landuse = self.landuse_instance
            defer_management_rebuild = bool(
                getattr(landuse, "_defer_disturbed_management_rebuild", False)
            )
            
            landuse.logger.info(f'Disturbed::on {evt}')
            with self.timed('  Remapping landuse'):
                landuse.logger.info(f'  Disturbed::Modifying landuse')
                self.remap_landuse(rebuild_managements=not defer_management_rebuild)
            
            with self.timed('  Calling spatialize_treecanopy hook'):
                ran_spatialize = self.spatialize_treecanopy()
                if ran_spatialize:
                    landuse.logger.info(f'  Disturbed::Modified landuse with treecanopy')

            if multi_ofe:
                landuse.logger.info(f'  Disturbed::Modifying MOFE soils')
                self.remap_mofe_landuse(rebuild_managements=not defer_management_rebuild)

        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            self.logger.info(f'  Routing to SOILS_BUILD_COMPLETE')
            soils = self.soils_instance
            if self.multi_ofe:
                with self.timed('  Modifying MOFE soils'):
                    soils.logger.info(f'  Disturbed::Modifying MOFE soils')
                    self.modify_mofe_soils()
            else:
                with self.timed('  Modifying soils'):
                    soils.logger.info(f'  Disturbed::Modifying soils')
                    self.modify_soils()

    def spatialize_treecanopy(self) -> int:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        wd = self.wd

        if 'treecanopy' in self.mods:
            from wepppy.nodb.mods.treecanopy import Treecanopy
            treecanopy = Treecanopy.getInstance(wd)
            treecanopy.acquire_raster()
            treecanopy.analyze()
        else:
            self.logger.info(f'  No treecanopy mod found')
            return 0

        self.logger.info(f'  Found treecanopy mod')
        landuse = self.landuse_instance

        with landuse.locked():
            self.logger.info(f'  Running spatialize_treecanopy')
            for topaz_id, treecanopy_pointdata in treecanopy:
                dom = landuse.domlc_d[topaz_id]
                man = landuse.managements[dom]

                if is_unburned_forest_disturbed_class(man.disturbed_class) and treecanopy:
                    _dom = '{}-{}'.format(dom, topaz_id)
                    _man = deepcopy(man)
                    _man.key = _dom
                    # this it not the right way to do it, because it will keep overwriting.
                    _man.cancov_override = round(treecanopy.data[topaz_id]) / 100.0
                    landuse.domlc_d[topaz_id] = _dom
                    landuse.managements[_dom] = _man

        return 1

    def get_sbs(self) -> Optional[SoilBurnSeverityMap]:
        wd = self.wd
        if not self.has_map:
            return

        disturbed_path = self._available_disturbed_path()
        if disturbed_path is None:
            return

        disturbed_cropped = self.disturbed_cropped
        if _exists(disturbed_cropped):
            os.remove(disturbed_cropped)

        dem_fn = Ron.getInstance(wd).dem_fn
        raster_stacker(disturbed_path, dem_fn, disturbed_cropped, resample='near')
        breaks, nodata_vals, color_map = self._sbs_map_args(disturbed_path)
        return SoilBurnSeverityMap(
            disturbed_cropped, breaks=breaks, nodata_vals=nodata_vals, color_map=color_map)

    def get_sbs_4class(self) -> SoilBurnSeverityMap:
        sbs = self.get_sbs()
        sbs.export_4class_map(self.sbs_4class_path)
        return SoilBurnSeverityMap(self.sbs_4class_path)
    
    def get_disturbed_key_lookup(self) -> Dict[str, str]:
        mapping_dict = self.landuse_instance.get_mapping_dict()
        d = {}
        for key in mapping_dict:
            disturbed_class = mapping_dict[key]['DisturbedClass'].replace(' ', '_')
            if not disturbed_class:  # filter '' and None
                continue
            if disturbed_class not in d:
                d[disturbed_class] = key

        assert 'forest_low_sev_fire' in d
        assert 'forest_moderate_sev_fire' in d
        assert 'forest_high_sev_fire' in d

        assert 'shrub_low_sev_fire' in d
        assert 'shrub_moderate_sev_fire' in d
        assert 'shrub_high_sev_fire' in d

        assert 'grass_low_sev_fire' in d
        assert 'grass_moderate_sev_fire' in d
        assert 'grass_high_sev_fire' in d

        return d

    def remap_landuse(self, *, rebuild_managements: bool = True) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        wd = self.wd

        landuse = self.landuse_instance

        disturbed_key_lookup = self.get_disturbed_key_lookup()
        landuse.logger.debug('  disturbed_key_lookup keys: %s', sorted(disturbed_key_lookup.keys()))
        #assert landuse.mode != LanduseMode.Single

        burn_shrubs = self.burn_shrubs
        burn_grass = self.burn_grass

        watershed = Watershed.getInstance(wd)

        sbs = self.get_sbs()
        meta = {}

        if sbs is None:
            return

        evaluated_hillslopes = 0
        channel_skips = 0
        burned_counts: Counter[str] = Counter()

        with landuse.locked():
            self._calc_sbs_coverage(sbs)

            landuse.logger.info('  Running burn-severity remap identify on %s', self.disturbed_cropped)
            key_value_counts = count_intersecting_raster_key_pairs(
                key_fn=watershed.subwta,
                key2_fn=self.disturbed_cropped,
                ignore_channels=True,
                ignore_keys=set(),
                ignore_keys2=set(),
            )
            global_value_counts: Counter[int] = Counter()
            for per_key_counts in key_value_counts.values():
                for raw_val, raw_count in per_key_counts.items():
                    global_value_counts[int(raw_val)] += int(raw_count)

            sbs_lc_d: Dict[str, str] = {}
            for key, per_key_counts in key_value_counts.items():
                if not per_key_counts:
                    continue
                mode_val = max(
                    ((int(raw_val), int(raw_count)) for raw_val, raw_count in per_key_counts.items()),
                    key=lambda item: (
                        item[1],
                        global_value_counts.get(item[0], 0),
                        item[0],
                    ),
                )[0]
                sbs_lc_d[str(key)] = str(mode_val)
            landuse.logger.info('  Completed burn-severity remap identify')
           
            class_pixel_map = sbs.class_pixel_map
            nodata_only_keys = 0

            landuse.logger.debug('  Iterating over %s remap hillslopes', len(landuse.domlc_d))
            for topaz_id in landuse.domlc_d:
                topaz_key = str(topaz_id)
                if (int(topaz_key) - 4) % 10 == 0:
                    channel_skips += 1
                    continue

                evaluated_hillslopes += 1
                dom = landuse.domlc_d[topaz_id]
                man = landuse.managements[dom]

                val = sbs_lc_d.get(topaz_key)
                if val is None:
                    burn_class = '130'
                    nodata_only_keys += 1
                else:
                    burn_class = class_pixel_map[val]
                landuse.logger.debug(
                    '    topaz_id=%s sbs_lc=%s dom=%s disturbed_class=%s burn_class=%s',
                    topaz_key,
                    val,
                    dom,
                    man.disturbed_class,
                    burn_class,
                )
                # topaz_id: 8632, sbs_lc: 2, dom: 42, man.disturbed_class: forest, burn_class: 255
                if burn_class in ['131', '132', '133']:
                    if is_unburned_forest_disturbed_class(man.disturbed_class):
                        landuse.logger.debug('     burning topaz_id=%s bucket=forest', topaz_key)
                        landuse.domlc_d[topaz_id] = {'131': disturbed_key_lookup['forest_low_sev_fire'], 
                                                     '132': disturbed_key_lookup['forest_moderate_sev_fire'], 
                                                     '133': disturbed_key_lookup['forest_high_sev_fire']}[burn_class]
                        burned_counts['forest'] += 1

                    elif man.disturbed_class == 'shrub' and burn_shrubs:
                        landuse.logger.debug('     burning topaz_id=%s bucket=shrub', topaz_key)
                        landuse.domlc_d[topaz_id] = {'131': disturbed_key_lookup['shrub_low_sev_fire'], 
                                                     '132': disturbed_key_lookup['shrub_moderate_sev_fire'], 
                                                     '133': disturbed_key_lookup['shrub_high_sev_fire']}[burn_class]
                        burned_counts['shrub'] += 1
                        
                    elif man.disturbed_class in ['tall grass'] and burn_grass:
                        landuse.logger.debug('     burning topaz_id=%s bucket=grass', topaz_key)
                        landuse.domlc_d[topaz_id] = {'131': disturbed_key_lookup['grass_low_sev_fire'], 
                                                     '132': disturbed_key_lookup['grass_moderate_sev_fire'], 
                                                     '133': disturbed_key_lookup['grass_high_sev_fire']}[burn_class]
                        burned_counts['grass'] += 1

                meta[topaz_key] = dict(burn_class=burn_class, disturbed_class=man.disturbed_class)

        total_burned = int(sum(burned_counts.values()))
        landuse.logger.info(
            '  Disturbed remap summary: evaluated=%s burned=%s (forest=%s shrub=%s grass=%s) nodata_only=%s unchanged=%s skipped_channels=%s',
            evaluated_hillslopes,
            total_burned,
            burned_counts.get('forest', 0),
            burned_counts.get('shrub', 0),
            burned_counts.get('grass', 0),
            nodata_only_keys,
            max(evaluated_hillslopes - total_burned, 0),
            channel_skips,
        )

        with self.locked():
            self._meta = meta

        if rebuild_managements:
            landuse = landuse.getInstance(wd)
            landuse.build_managements()
        else:
            landuse.logger.debug('  Skipping immediate landuse.build_managements() due to deferred rebuild contract')

    @property
    def meta(self) -> Dict[str, Dict[str, str]]:
        if not hasattr(self, '_meta'):
            self.remap_landuse()

        return self._meta
    
    def build_extended_land_soil_lookup(self) -> None:
        import csv
        from wepppy.wepp.management import load_map, get_management, IniLoopCropland
        from wepppy.nodb.mods.disturbed import read_disturbed_land_soil_lookup

        import os

        hdr = ['key', 'desc', 'man', 'disturbed_class',
            'ini.data.bdtill', 'ini.data.cancov', 'ini.data.daydis', 'ini.data.dsharv', 'ini.data.frdp', 
            'ini.data.inrcov', 'ini.data.iresd', 'ini.data.imngmt', 'ini.data.rfcum', 'ini.data.rhinit',
            'ini.data.rilcov', 'ini.data.rrinit', 'ini.data.rspace', 'ini.data.rtyp', 'ini.data.snodpy',
            'ini.data.thdp', 'ini.data.tillay1', 'ini.data.tillay2', 'ini.data.width', 'ini.data.sumrtm',
            'ini.data.sumsrm',
            'plant.data.bb', 'plant.data.bbb', 'plant.data.beinp', 'plant.data.btemp', 'plant.data.cf', 
            'plant.data.crit', 'plant.data.critvm', 'plant.data.cuthgt', 'plant.data.decfct', 'plant.data.diam', 
            'plant.data.dlai', 'plant.data.dropfc', 'plant.data.extnct', 'plant.data.fact', 'plant.data.flivmx', 
            'plant.data.gddmax', 'plant.data.hi', 'plant.data.hmax',
            'plant.data.mfocod',
            'plant.data.oratea', 'plant.data.orater', 'plant.data.otemp', 'plant.data.pltol',
            'plant.data.pltsp', 'plant.data.rdmax', 'plant.data.rsr', 'plant.data.rtmmax', 
            'plant.data.spriod', 'plant.data.tmpmax', 'plant.data.tmpmin',
            'plant.data.xmxlai', 'plant.data.yld']
                
                
        mapping = Landuse.getInstance(self.wd).mapping
        d = load_map(mapping)

        man_d = {}
        man_d_base = {}
        for k in d:
            m = get_management(k, _map=mapping)
            # Ini.loop.landuse.cropland (6.6 inrcov), (9.3 rilcov)

            assert len(m.inis) == 1
            assert m.inis[0].landuse == 1
            assert isinstance(m.inis[0].data, IniLoopCropland)
            cancov, inrcov, rilcov = m.inis[0].data.cancov, m.inis[0].data.inrcov, m.inis[0].data.rilcov
            man_fn = d[k]['ManagementFile']
            disturbed_class = d[k].get('DisturbedClass', '-')

            row = [('{%s}' % v).format(key=k, desc=m.desc, man=man_fn, 
                                    disturbed_class=disturbed_class,
                                    ini=m.inis[0],
                                    plant=m.plants[0]) for v in hdr]

            man_d[disturbed_class] = dict(zip(hdr, row))
            # Base-class fallback keeps lookup rows keyed by canonical classes
            # like "thinning" even when management map entries are variant forms
            # such as "thinning_40_90".
            base_class = disturbed_class
            if isinstance(base_class, str):
                if 'mulch' in base_class:
                    base_class = 'mulch'
                elif 'thinning' in base_class:
                    base_class = 'thinning'
            if isinstance(base_class, str) and base_class not in man_d_base:
                man_d_base[base_class] = man_d[disturbed_class]

        self.ensure_land_soil_lookup_schema()
        landsoil_lookup = self.land_soil_replacements_d
        extended_landsoil_lookup = self._new_extended_land_soil_lookup_tmp_path()

        wtr = None
        try:
            with open(extended_landsoil_lookup, 'w') as f:
                for (texid, disturbed_class), _d in landsoil_lookup.items():
                    man_row = man_d.get(disturbed_class) or man_d_base.get(disturbed_class)
                    if man_row is None:
                        print(f'No management found for {disturbed_class} in man_d')
                        continue

                    _d.update(man_row)

                    sev_enum = 0
                    raw_luse_value = _d.get('luse')
                    if raw_luse_value is None or str(raw_luse_value).strip() == '':
                        luse_value = disturbed_class
                    else:
                        luse_value = raw_luse_value
                    if 'high sev' in disturbed_class:
                        sev_enum = 4
                    elif 'moderate sev' in disturbed_class:
                        sev_enum = 3
                    elif 'low sev' in disturbed_class:
                        sev_enum = 2
                    elif 'prescribed' in disturbed_class:
                        sev_enum = 1

                    luse = f'{luse_value}'

                    if 'forest' in luse:
                        luse = 'forest'
                    elif 'grass' in luse and 'short' not in luse:
                        luse = 'tall grass'
                    elif 'shrub' in luse:
                        luse = 'shrub'

                    _d = {'sev_enum': sev_enum,  'landuse': luse, 'disturbed_class': disturbed_class, **_d}
                    # Preserve base-table lookup key naming in extended exports so
                    # downstream artifact labels keep the expected disturbed class.
                    _d['luse'] = f'{luse_value}'
                    # Keep canonical disturbed class from lookup key for downstream
                    # soil replacement lookups (for example, ("silt loam", "thinning")).
                    _d['disturbed_class'] = disturbed_class

                    if 'rdmax' in _d:
                        _d['plant.data.rdmax'] = _d['rdmax']
                        del _d['rdmax']
                    elif 'plant.data.rdmax' not in _d:
                        _d['plant.data.rdmax'] = None

                    if 'xmxlai' in _d:
                        _d['plant.data.xmxlai'] = _d['xmxlai']
                        del _d['xmxlai']
                    elif 'plant.data.xmxlai' not in _d:
                        _d['plant.data.xmxlai'] = None

                    if wtr is None:
                        wtr = csv.DictWriter(f, fieldnames=_d.keys())
                        wtr.writeheader()

                    wtr.writerow(_d)

            os.replace(extended_landsoil_lookup, self.extended_lookup_fn)
        finally:
            if _exists(extended_landsoil_lookup):
                os.remove(extended_landsoil_lookup)

    def _new_extended_land_soil_lookup_tmp_path(self) -> str:
        """Create a run-scoped writable temporary CSV path for extended lookup generation."""
        os.makedirs(self.disturbed_dir, exist_ok=True)
        fd, path = tempfile.mkstemp(
            prefix='extended_disturbed_land_soil_lookup.',
            suffix='.csv',
            dir=self.disturbed_dir,
        )
        os.close(fd)
        return path

    def remap_mofe_landuse(self, *, rebuild_managements: bool = True) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        wd = self.wd

        landuse = self.landuse_instance

        watershed = Watershed.getInstance(wd)

        sbs = self.get_sbs()

        if sbs is None:
            return

        evaluated_segments = 0
        burned_counts: Counter[str] = Counter()

        with landuse.locked():
            self._calc_sbs_coverage(sbs)

            sbs_lc_d = sbs.build_lcgrid(watershed.subwta, watershed.mofe_map)

            for topaz_id in landuse.domlc_mofe_d:
                for _id in landuse.domlc_mofe_d[topaz_id]:
                    evaluated_segments += 1
                    burn_class = str(sbs_lc_d[topaz_id][_id])
                    dom = landuse.domlc_mofe_d[topaz_id][_id]
                    man = landuse.managements[dom]
                    landuse.logger.debug(
                        '    mofe topaz_id=%s ofe=%s dom=%s disturbed_class=%s burn_class=%s',
                        topaz_id,
                        _id,
                        dom,
                        man.disturbed_class,
                        burn_class,
                    )

                    # TODO: probably a better way to do this based on the disturbed_class
                    if burn_class in ['131', '132', '133']:
                        if is_unburned_forest_disturbed_class(man.disturbed_class):
                            landuse.domlc_mofe_d[topaz_id][_id] = {'131': '106', '132': '118', '133': '105'}[burn_class]
                            burned_counts['forest'] += 1

                        elif man.disturbed_class == 'shrub':
                            landuse.domlc_mofe_d[topaz_id][_id] = {'131': '121', '132': '120', '133': '119'}[burn_class]
                            burned_counts['shrub'] += 1

                        elif man.disturbed_class in ['short grass', 'tall grass']:
                            landuse.domlc_mofe_d[topaz_id][_id] = {'131': '131', '132': '130', '133': '129'}[burn_class]
                            burned_counts['grass'] += 1

        total_burned = int(sum(burned_counts.values()))
        landuse.logger.info(
            '  Disturbed MOFE remap summary: evaluated=%s burned=%s (forest=%s shrub=%s grass=%s) unchanged=%s',
            evaluated_segments,
            total_burned,
            burned_counts.get('forest', 0),
            burned_counts.get('shrub', 0),
            burned_counts.get('grass', 0),
            max(evaluated_segments - total_burned, 0),
        )

        if rebuild_managements:
            landuse = landuse.getInstance(wd)
            landuse.build_managements()
        else:
            landuse.logger.debug('  Skipping immediate landuse.build_managements() due to deferred rebuild contract')

    @property
    def lookup_fn(self) -> str:
        _lookup = _join(self.disturbed_dir, 'disturbed_land_soil_lookup.csv')

        if not _exists(_lookup):
            self.reset_land_soil_lookup(reason='missing_lookup_autorecover')

        return _lookup

    @property
    def extended_lookup_fn(self) -> str:
        return _join(self.disturbed_dir, 'disturbed_land_soil_lookup_extended.csv')

    @property
    def active_lookup_fn(self) -> str:
        base_lookup_fn = self.lookup_fn
        extended_lookup_fn = self.extended_lookup_fn
        if self.active_lookup_variant == self.LOOKUP_VARIANT_EXTENDED and _exists(extended_lookup_fn):
            return extended_lookup_fn
        return base_lookup_fn

    def ensure_land_soil_lookup_schema(self) -> None:
        upgraded = upgrade_disturbed_land_soil_lookup(
            self.lookup_fn,
            self.default_land_soil_lookup_fn,
        )
        if upgraded:
            self.logger.info('  upgraded disturbed lookup schema in place')

    @property
    def land_soil_replacements_d(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        self.ensure_land_soil_lookup_schema()
        default_fn = self.default_land_soil_lookup_fn
        base_lookup_fn = self.lookup_fn
        active_lookup_fn = self.active_lookup_fn

        lookup = read_disturbed_land_soil_lookup(active_lookup_fn)

        expected_thinning_keys = {
            ('clay loam', 'thinning'),
            ('loam', 'thinning'),
            ('sand loam', 'thinning'),
            ('silt loam', 'thinning'),
        }
        if any(key not in lookup for key in expected_thinning_keys):
            fallback_lookups = []
            if _exists(base_lookup_fn):
                fallback_lookups.append(read_disturbed_land_soil_lookup(base_lookup_fn))
            fallback_lookups.append(read_disturbed_land_soil_lookup(default_fn))
            for key in expected_thinning_keys:
                if key in lookup:
                    continue
                for fallback_lookup in fallback_lookups:
                    if key in fallback_lookup:
                        lookup[key] = fallback_lookup[key]
                        break

        return lookup

    def pmetpara_prep(self) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        from wepppy.nodb.core import Wepp
        from wepppy.runtime_paths.wepp_inputs import materialize_input_file
        _land_soil_replacements_d = self.land_soil_replacements_d

        wd = self.wd
        landuse = self.landuse_instance
        soils = self.soils_instance
        wepp = Wepp.getInstance(wd)

        self.logger.info('  Identifying landuse for pmetpara.txt')
        domlc_d = {}
        for topaz_id, dom in landuse.domlc_d.items():
            if (int(topaz_id) - 4) % 10 == 0:
                continue
            domlc_d[topaz_id] = dom

        n = len(domlc_d)
        soil_texture_d: Dict[str, Tuple[Any, Any]] = {}

        with open(_join(wepp.runs_dir, 'pmetpara.txt'), 'w') as fp:
            fp.write('{n}\n'.format(n=n))

            for i, (topaz_id, dom) in enumerate(domlc_d.items()):
                self.logger.info(f'    pmetpara.txt gen for topaz_id: {topaz_id}, dom: {dom}')

                man_summary = landuse.managements[dom]
                man = man_summary.get_management()

                mukey = soils.domsoil_d[topaz_id]
                if mukey in soil_texture_d:
                    clay, sand = soil_texture_d[mukey]
                else:
                    _soil = soils.soils[mukey]
                    clay = None
                    sand = None

                    soil_fname = getattr(_soil, 'fname', None)
                    if isinstance(soil_fname, str) and soil_fname:
                        try:
                            soil_src = materialize_input_file(
                                wd,
                                f'soils/{soil_fname}',
                                purpose='disturbed-pmet-soil-texture',
                            )
                            soilu = WeppSoilUtil(soil_src)
                            clay = soilu.clay
                            sand = soilu.sand
                        except Exception as exc:
                            self.logger.warning(
                                f'      failed archive-first soil texture for {mukey} ({soil_fname}): {exc}'
                            )

                    if not (isfloat(clay) and isfloat(sand)):
                        clay = _soil.clay
                        sand = _soil.sand

                    soil_texture_d[mukey] = (clay, sand)

                assert isfloat(clay), clay
                assert isfloat(sand), sand

                texid = simple_texture(clay=clay, sand=sand)
                disturbed_class = man_summary.disturbed_class

                if disturbed_class is not None:
                    lookup_class = lookup_disturbed_class(disturbed_class)
                    if lookup_class == disturbed_class and 'mulch' in disturbed_class:
                        disturbed_class = 'mulch'
                    elif lookup_class == disturbed_class and 'thinning' in disturbed_class:
                        disturbed_class = 'thinning'
                    else:
                        disturbed_class = lookup_class

                replacements = _land_soil_replacements_d.get((texid, disturbed_class))
                if disturbed_class is None or disturbed_class == '' or 'developed' in disturbed_class:
                    self.logger.info('      setting kcb and rawp for unclassified disturbed_class or developed')
                    kcb = 0.95
                    rawb = 0.80
                elif replacements is None:
                    self.logger.info(
                        f'      no land_soil_lookup entry for {texid}-{disturbed_class}; using defaults'
                    )
                    kcb = 0.95
                    rawb = 0.80
                else:
                    self.logger.info(f'      setting kcb and rawp for {texid}-{disturbed_class} from land_soil_lookup')
                    kcb = replacements['pmet_kcb']
                    rawb = replacements['pmet_rawp']

                description = f'{texid}-{disturbed_class}'.replace(' ', '_')
                plant_name = man.plants[0].name
                fp.write(f'{plant_name},{kcb},{rawb},{i+1},{description}\n')

    def _resolve_source_soil_path(
        self,
        soils_instance: 'Soils',
        soil_fname: str,
        *,
        topaz_id: str,
        mukey: str,
        soil_summary_dir: Optional[str] = None,
    ) -> str:
        if not isinstance(soil_fname, str) or not soil_fname:
            raise FileNotFoundError(
                f"Cannot resolve source soil file for topaz_id={topaz_id!r}, mukey={mukey!r}: missing soil filename"
            )

        local_soil_path = _join(soils_instance.soils_dir, soil_fname)
        if _exists(local_soil_path):
            return local_soil_path

        checked_paths = [local_soil_path]

        if isinstance(soil_summary_dir, str) and soil_summary_dir:
            summary_soil_path = _join(soil_summary_dir, soil_fname)
            if summary_soil_path not in checked_paths:
                checked_paths.append(summary_soil_path)
                if _exists(summary_soil_path):
                    self.logger.info(
                        "Using summary soil path for topaz_id=%s mukey=%s: %s",
                        topaz_id,
                        mukey,
                        summary_soil_path,
                    )
                    return summary_soil_path

        parent_wd = getattr(soils_instance, "parent_wd", None)
        if isinstance(parent_wd, str) and parent_wd:
            parent_soil_path = _join(parent_wd, "soils", soil_fname)
            if parent_soil_path not in checked_paths:
                checked_paths.append(parent_soil_path)
                if _exists(parent_soil_path):
                    self.logger.info(
                        "Using parent soil path for topaz_id=%s mukey=%s: %s",
                        topaz_id,
                        mukey,
                        parent_soil_path,
                    )
                    return parent_soil_path

        checked = ", ".join(checked_paths)
        raise FileNotFoundError(
            f"Missing source soil file for topaz_id={topaz_id!r}, mukey={mukey!r}. Checked: {checked}"
        )

    def modify_mofe_soils(self) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        wd = self.wd
        sol_ver = self.sol_ver

        _ = Ron.getInstance(wd)
        landuse = self.landuse_instance
        soils = self.soils_instance

        _land_soil_replacements_d = self.land_soil_replacements_d
        recompute_wp_fc_using_rosetta_on_bd_override = bool(
            getattr(soils, 'rosetta_wc_fc_from_disturbed_bd_override', False)
        )

        soils.logger.info(f'Disturbed::modify_mofe_soils, sol_ver: {sol_ver}')

        generation_tasks: List[Dict[str, Any]] = []
        hillslope_plans: List[Dict[str, Any]] = []
        processed_hillslopes = 0
        processed_segments = 0

        with soils.locked():
            planned_soil_keys = set(soils.soils.keys())

            for topaz_id, mukey in soils.domsoil_d.items():
                if str(topaz_id).endswith('4'):
                    continue

                processed_hillslopes += 1
                self.logger.debug('  topaz_id=%s mukey=%s', topaz_id, mukey)
                soils.logger.debug('  topaz_id=%s mukey=%s', topaz_id, mukey)

                stack: List[str] = []
                desc: List[str] = []

                _soil = soils.soils[mukey]
                clay = _soil.clay
                sand = _soil.sand

                assert isfloat(clay), clay
                assert isfloat(sand), sand

                texid = simple_texture(clay=clay, sand=sand)
                source_soil_path = self._resolve_source_soil_path(
                    soils,
                    getattr(_soil, 'fname', None),
                    topaz_id=str(topaz_id),
                    mukey=str(mukey),
                    soil_summary_dir=getattr(_soil, 'soils_dir', None),
                )

                assert len(landuse.domlc_mofe_d[topaz_id]) > 0, topaz_id

                for _id in sorted([int(_id) for _id in landuse.domlc_mofe_d[topaz_id]]):
                    _id = str(_id)
                    processed_segments += 1
                    
                    dom = landuse.domlc_mofe_d[topaz_id][_id]
                    man = landuse.managements[dom]

                    assert man is not None, dom

                    lookup_class = lookup_disturbed_class(man.disturbed_class)
                    key = (texid, lookup_class)
                    replacements = _land_soil_replacements_d.get(key, None)

                    if replacements is None:  # e.g. developed low intensity
                        if sol_ver == 9002.0:
                            # MOFE 9002 stacks must stay same-version for SoilMultipleOfeSynth.
                            # On lookup miss we keep lookup-driven erodibility untouched while
                            # migrating into an explicit class-specific 9002 fallback soil.
                            replacements = dict(
                                luse=man.disturbed_class,
                                stext=texid,
                                ksatfac=0.0,
                                ksatrec=0.0
                            )
                            disturbed_mukey = f'{mukey}-{texid}-{man.disturbed_class}'
                        else:
                            disturbed_mukey = f'{mukey}-{texid}'
                    else:
                        disturbed_mukey = f'{mukey}-{texid}-{man.disturbed_class}'

                    disturbed_fn = f'{disturbed_mukey}.sol'
                    output_path = _join(soils.soils_dir, disturbed_fn)
                    if disturbed_mukey not in planned_soil_keys:
                        _h0_max_om = None
                        if man.disturbed_class is not None and 'fire' in man.disturbed_class:
                            _h0_max_om = self.h0_max_om

                        generation_tasks.append(
                            dict(
                                disturbed_mukey=disturbed_mukey,
                                disturbed_fn=disturbed_fn,
                                source_soil_path=source_soil_path,
                                output_path=output_path,
                                replacements=dict(replacements) if replacements is not None else None,
                                sol_ver=sol_ver,
                                h0_max_om=_h0_max_om,
                                recompute_wp_fc_using_rosetta_on_bd_override=(
                                    recompute_wp_fc_using_rosetta_on_bd_override
                                ),
                                desc=f'{_soil.desc} - {man.disturbed_class}',
                                meta_fn=_soil.meta_fn,
                            )
                        )
                        planned_soil_keys.add(disturbed_mukey)

                    desc.append(f'{man.disturbed_class}')
                    stack.append(output_path)

                key = f'hill_{topaz_id}.mofe'
                hillslope_plans.append(
                    dict(
                        topaz_id=topaz_id,
                        key=key,
                        sol_fn=f'{key}.sol',
                        stack=stack,
                        desc='|'.join(desc),
                    )
                )

        self.logger.info(
            '  Prepared MOFE soil modification plans: hillslopes=%s segments=%s generation_tasks=%s',
            processed_hillslopes,
            processed_segments,
            len(generation_tasks),
        )

        cpu_count = os.cpu_count() or 1
        ncpu_override = os.getenv('WEPPPY_NCPU')
        max_workers = NCPU if ncpu_override else cpu_count

        if max_workers < 1:
            max_workers = 1
        if ncpu_override:
            if max_workers > NCPU:
                max_workers = NCPU
        elif max_workers > max(cpu_count, 20):
            max_workers = max(cpu_count, 20)

        if generation_tasks:
            max_workers = min(max_workers, len(generation_tasks))

        def _run_mofe_soil_pool(prefer_spawn: bool) -> None:
            with createProcessPoolExecutor(
                max_workers=max_workers,
                logger=self.logger,
                prefer_spawn=prefer_spawn,
            ) as executor:
                futures = [executor.submit(_build_disturbed_mofe_soil, task) for task in generation_tasks]
                futures_n = len(futures)
                count = 0
                pending_futures = set(futures)
                last_progress_time = time.time()

                while pending_futures:
                    done, pending_futures = wait(
                        pending_futures, timeout=5, return_when=FIRST_COMPLETED
                    )

                    if not done:
                        since_progress = time.time() - last_progress_time
                        pending_count = len(pending_futures)

                        if since_progress >= 60:
                            self.logger.error(
                                '  MOFE disturbed soil tasks still pending after %.1fs; %s tasks waiting.',
                                round(since_progress, 1),
                                pending_count,
                            )
                        else:
                            self.logger.info(
                                '  Waiting on MOFE disturbed soil tasks (pending=%s, %.1fs since last completion).',
                                pending_count,
                                round(since_progress, 1),
                            )
                        continue

                    for future in done:
                        try:
                            disturbed_mukey, elapsed_time = future.result()
                            count += 1
                            self.logger.debug(
                                '  (%s/%s) Completed MOFE disturbed soil build for %s in %ss',
                                count,
                                futures_n,
                                disturbed_mukey,
                                elapsed_time,
                            )
                            last_progress_time = time.time()
                        except BrokenProcessPool as exc:
                            self.logger.error(
                                '  MOFE disturbed soil process pool terminated unexpectedly: %s',
                                exc,
                            )
                            for pending_future in pending_futures:
                                pending_future.cancel()
                            raise
                        except Exception:
                            for pending_future in pending_futures:
                                pending_future.cancel()
                            raise

        def _run_mofe_soil_sequential() -> None:
            total = len(generation_tasks)
            self.logger.warning('  Running MOFE disturbed soil generation sequentially')
            for idx, task in enumerate(generation_tasks, start=1):
                disturbed_mukey, elapsed_time = _build_disturbed_mofe_soil(task)
                self.logger.debug(
                    '  (%s/%s) Completed MOFE disturbed soil build for %s in %ss [sequential]',
                    idx,
                    total,
                    disturbed_mukey,
                    elapsed_time,
                )

        if generation_tasks:
            run_concurrent = max_workers > 1 and len(generation_tasks) > 1
            self.logger.info(
                '  Prepared %s MOFE disturbed soil generation task(s) with max_workers=%s',
                len(generation_tasks),
                max_workers,
            )
            if run_concurrent:
                self.logger.info('  Submitting MOFE disturbed soil tasks to ProcessPoolExecutor')
                try:
                    _run_mofe_soil_pool(prefer_spawn=True)
                except BrokenProcessPool as exc:
                    self.logger.warning(
                        '  Retrying MOFE disturbed soil pool with fork-based executor after spawn failure (%s)',
                        exc,
                    )
                    try:
                        _run_mofe_soil_pool(prefer_spawn=False)
                    except BrokenProcessPool as retry_exc:
                        self.logger.warning(
                            '  Falling back to sequential MOFE disturbed soil generation after process pool failures (%s)',
                            retry_exc,
                        )
                        _run_mofe_soil_sequential()
            else:
                _run_mofe_soil_sequential()
        else:
            self.logger.info('  No MOFE disturbed soils required regeneration.')

        for idx, hillslope_plan in enumerate(hillslope_plans, start=1):
            with self.timed('  Generating MOFE soil file with SoilMultipleOfeSynth'):
                mofe_synth = SoilMultipleOfeSynth(stack=hillslope_plan['stack'])
                mofe_synth.write(_join(soils.soils_dir, hillslope_plan['sol_fn']))

            self.logger.debug(
                '  (%s/%s) Generated MOFE soil file for topaz_id=%s',
                idx,
                len(hillslope_plans),
                hillslope_plan['topaz_id'],
            )

        self.logger.info(
            '  Completed MOFE soil generation: regenerated_soils=%s hillslope_files=%s',
            len(generation_tasks),
            len(hillslope_plans),
        )

        with soils.locked():
            for task in generation_tasks:
                disturbed_mukey = task['disturbed_mukey']
                if disturbed_mukey not in soils.soils:
                    soils.soils[disturbed_mukey] = SoilSummary(
                        mukey=disturbed_mukey,
                        fname=task['disturbed_fn'],
                        soils_dir=soils.soils_dir,
                        desc=task['desc'],
                        meta_fn=task['meta_fn'],
                        build_date=str(datetime.now()),
                    )

            for hillslope_plan in hillslope_plans:
                topaz_id = hillslope_plan['topaz_id']
                key = hillslope_plan['key']
                soils.domsoil_d[topaz_id] = key
                soils.soils[key] = SoilSummary(
                    mukey=key,
                    fname=hillslope_plan['sol_fn'],
                    soils_dir=soils.soils_dir,
                    desc=hillslope_plan['desc'],
                    meta_fn=None,
                    build_date=str(datetime.now()),
                )

            with self.timed('  Recalculating soil areas and pct_coverage'):
                watershed = self.watershed_instance

                for k in soils.soils:
                    soils.soils[k].area = 0.0

                total_area = 0.0
                for topaz_id, k in soils.domsoil_d.items():
                    sub_area = watershed.hillslope_area(topaz_id)
                    soils.soils[k].area += sub_area
                    total_area += sub_area

                if total_area <= 0.0:
                    soils.logger.warning(
                        'Disturbed:: total_area is 0.0; setting soil pct_coverage to 0.0'
                    )
                    for k in soils.soils:
                        soils.soils[k].pct_coverage = 0.0
                else:
                    for k in soils.soils:
                        coverage = 100.0 * soils.soils[k].area / total_area
                        soils.soils[k].pct_coverage = coverage

    def modify_soil(
        self, 
        topaz_id: str, 
        landuse_instance: 'Landuse', 
        soils_instance: 'Soils', 
        _land_soil_replacements_d: Dict[Tuple[str, str], Dict[str, Any]]
    ) -> str:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(topaz_id={topaz_id})')

        wd = self.wd
        sol_ver = self.sol_ver

        mukey = soils_instance.domsoil_d[topaz_id]
        dom = landuse_instance.domlc_d[topaz_id]
        man = landuse_instance.managements[dom]
        recompute_wp_fc_using_rosetta_on_bd_override = bool(
            getattr(soils_instance, 'rosetta_wc_fc_from_disturbed_bd_override', False)
        )

        soils_instance.logger.info(f'  Disturbed:: Disturbed.modify_soil(topaz_id={topaz_id}, mukey={mukey}, dom={dom})')

        disturbed_mukey = None
        if man.sol_path:
            self.logger.info(f'  Using soil file from man.sol_path {man.sol_path}')
            disturbed_mukey = _split(man.sol_fn)[-1].replace('.sol', '')
            sol_fn =  f'{disturbed_mukey}.sol'
            new_sol_path = _join(soils_instance.soils_dir, sol_fn)

            if not _exists(new_sol_path):
                shutil.copyfile(man.sol_path, new_sol_path)

            if disturbed_mukey not in soils_instance.soils:
                soils_instance.soils[disturbed_mukey] = SoilSummary(mukey=disturbed_mukey,
                                                            fname=sol_fn,
                                                            soils_dir=soils_instance.soils_dir,
                                                            desc=disturbed_mukey,
                                                            meta_fn=None,
                                                            build_date=str(datetime.now()))
        else:
            self.logger.info(f'  Identifying soil')
            _soil = soils_instance.soils[mukey]
            clay = _soil.clay
            sand = _soil.sand

            assert isfloat(clay), clay
            assert isfloat(sand), sand

            texid = simple_texture(clay=clay, sand=sand)

            # Use base disturbed class for lookup (strip treatment suffixes like -mulch_15)
            # Treatment-modified classes (e.g., 'forest moderate sev fire-mulch_15') won't have
            # entries in _land_soil_replacements_d, but we still need fire-adjusted erodibility
            lookup_class = lookup_disturbed_class(man.disturbed_class)
            key = (texid, lookup_class)
            if key not in _land_soil_replacements_d:
                # this is different from mofe.
                # for mofe we have to migrate to 9002...
                return mukey

            disturbed_mukey = f'{mukey}-{texid}-{man.disturbed_class}'

            if disturbed_mukey not in soils_instance.soils:
                self.logger.info(f'  Generating disturbed soil for topaz_id: {topaz_id}, mukey: {mukey}, dom: {dom}, disturbed_mukey: {disturbed_mukey}')
                disturbed_fn = disturbed_mukey + '.sol'
                replacements = dict(_land_soil_replacements_d[key])

                if 'fire' in man.disturbed_class:
                    _h0_max_om = self.h0_max_om
                else:
                    _h0_max_om = None

                soil_u = WeppSoilUtil(
                    self._resolve_source_soil_path(
                        soils_instance,
                        getattr(_soil, 'fname', None),
                        topaz_id=str(topaz_id),
                        mukey=str(mukey),
                        soil_summary_dir=getattr(_soil, 'soils_dir', None),
                    )
                )
                if sol_ver == 7778.0:
                    new = soil_u.to_7778disturbed(
                        replacements,
                        h0_max_om=_h0_max_om,
                        recompute_wp_fc_using_rosetta_on_bd_override=(
                            recompute_wp_fc_using_rosetta_on_bd_override
                        ),
                    )
                else:
                    new = soil_u.to_over9000(
                        replacements,
                        h0_max_om=_h0_max_om,
                        recompute_wp_fc_using_rosetta_on_bd_override=(
                            recompute_wp_fc_using_rosetta_on_bd_override
                        ),
                        version=sol_ver,
                    )

                new.write(_join(soils_instance.soils_dir, disturbed_fn))

                desc = f'{_soil.desc} - {man.disturbed_class}'
                soils_instance.soils[disturbed_mukey] = SoilSummary(mukey=disturbed_mukey,
                                                            fname=disturbed_fn,
                                                            soils_dir=soils_instance.soils_dir,
                                                            desc=desc,
                                                            meta_fn=_soil.meta_fn,
                                                            build_date=str(datetime.now()))

        assert disturbed_mukey is not None, (topaz_id, mukey, dom)
        return disturbed_mukey

    def modify_soils(self) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        wd = self.wd
        landuse = self.landuse_instance
        soils = self.soils_instance
        watershed = self.watershed_instance
        _land_soil_replacements_d = self.land_soil_replacements_d

        soils.logger.info(f'Disturbed::  Disturbed.modify_soils, sol_ver: {self.sol_ver}')

        with soils.locked():
            for k in soils.soils:
                soils.soils[k].area = 0.0

            total_area = 0.0
            for topaz_id, mukey in soils.domsoil_d.items():

                # if is channel skip
                if (int(topaz_id) - 4) % 10 == 0:
                    continue

                disturbed_mukey = self.modify_soil(str(topaz_id), landuse, soils, _land_soil_replacements_d)
                assert disturbed_mukey is not None, topaz_id

                soils.domsoil_d[topaz_id] = disturbed_mukey
                sub_area = watershed.hillslope_area(topaz_id)

                soils.soils[disturbed_mukey].area += sub_area
                total_area += sub_area

            # need to recalculate the pct_coverages
            if total_area <= 0.0:
                soils.logger.warning(
                    'Disturbed:: total_area is 0.0; setting soil pct_coverage to 0.0'
                )
                for k in soils.soils:
                    soils.soils[k].pct_coverage = 0.0
            else:
                for k in soils.soils:
                    coverage = 100.0 * soils.soils[k].area / total_area
                    soils.soils[k].pct_coverage = coverage

    def _calc_sbs_coverage(self, sbs: Optional[SoilBurnSeverityMap]) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(sbs={sbs})')

        with self.locked():
            if sbs is None:
                self.sbs_coverage = {
                    'noburn': 1.0,
                    'low': 0.0,
                    'moderate': 0.0,
                    'high': 0.0
                }
            else:
                watershed = self.watershed_instance
                bounds, transform, proj = read_raster(watershed.bound)

                if not sbs.data.shape == bounds.shape:
                    raise Exception(f'SBS map and watershed.bound do not align: {sbs.data.shape} != {bounds.shape}')

                assert sbs.data.shape == bounds.shape, [sbs.data.shape, bounds.shape]


                c = Counter(sbs.data[np.where(bounds == 1.0)])

                total_px = float(sum(c.values()))

                # todo: calcuate based on disturbed burn classes
                self.sbs_coverage = {
                                     'noburn': c[130] / total_px,
                                     'low': c[131] / total_px,
                                     'moderate': c[132] / total_px,
                                     'high': c[133] / total_px
                                     }
        
