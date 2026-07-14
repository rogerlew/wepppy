"""AgFields NoDb controller.

This module manages agricultural field workflows in WEPPcloud. It validates
field boundary GeoJSON, abstracts sub-fields with Peridot, prepares crop
rotation managements, and launches WEPP runs per sub-field. Outputs include
normalized GeoJSON, raster maps, parquet summaries, and WEPP loss reports that
drive agricultural dashboards and treatment comparisons.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import time
import zipfile
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from copy import deepcopy
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

import pandas as pd

from wepp_runner.wepp_runner import get_linux_wepp_bin_opts, run_hillslope

from wepppy.all_your_base.all_your_base import isint
from wepppy.nodb.base import NoDbBase, nodb_setter
from wepppy.nodb.core import Climate, ClimateMode, Landuse, Watershed
from wepppy.nodb.geojson_crs_inference import infer_geojson_crs
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.topo.peridot.peridot_runner import (
    post_abstract_sub_fields,
    run_peridot_wbt_sub_fields_abstraction,
)
from wepppy.topo.watershed_abstraction.slope_file import clip_slope_file_length
from wepppy.wepp.management import InvalidManagementKey, get_management_summary, load_map
from wepppy.wepp.management.managements import ScenarioReference, read_management
from wepppy.wepp.management.utils import ManagementRotationSynth, downgrade_to_98_4_format

from os.path import exists as _exists
from os.path import join as _join

try:
    from wepppy.query_engine import update_catalog_entry as _update_catalog_entry
except ImportError:  # pragma: no cover - optional dependency
    _update_catalog_entry = None

__all__ = [
    'AgFieldsNoDbLockedException',
    'AgFieldsRunError',
    'PlantFileProcessingError',
    'RotationLookupValidationError',
    'AgFields',
]

_APPLIED_RESIDUE_HMAX_FLOOR_M = 0.00001
_APPLIED_RESIDUE_HMAX_REASON = 'applied_residue_positive_hmax_required_by_wepp'


class AgFieldsNoDbLockedException(Exception):
    pass


class AgFieldsRunError(RuntimeError):
    def __init__(self, field_id: int, sub_field_id: int, message: str) -> None:
        self.field_id = int(field_id)
        self.sub_field_id = int(sub_field_id)
        super().__init__(
            f'WEPP sub-field run failed for sub_field_id={self.sub_field_id}, '
            f'field_id={self.field_id}: {message}'
        )


class PlantFileProcessingError(ValueError):
    def __init__(self, filename: str, message: str) -> None:
        self.filename = filename
        super().__init__(f'Plant file processing failed for "{filename}": {message}')


class RotationLookupValidationError(ValueError):
    def __init__(self, results: List[Dict[str, Any]]) -> None:
        self.results = results
        super().__init__('Rotation lookup contains invalid mapped rows.')


class AgFields(NoDbBase):
    """Controller responsible for agricultural field prep, validation, and WEPP runs."""
    __name__ = 'AgFields'

    __exclude__ = ('_w3w', 
                   '_locales', 
                   '_enable_landuse_change',
                   '_dem_db',
                   '_boundary')

    filename = 'ag_fields.nodb'

    def __init__(
        self,
        wd: str,
        cfg_fn: str = 'disturbed_9002.cfg',
        run_group: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            if not _exists(self.ag_field_wepp_runs_dir):
                os.makedirs(self.ag_field_wepp_runs_dir)

            if not _exists(self.ag_field_wepp_output_dir):
                os.makedirs(self.ag_field_wepp_output_dir)

            if not _exists(self.ag_fields_dir):
                os.makedirs(self.ag_fields_dir)

            if not _exists(self.plant_files_dir):
                os.makedirs(self.plant_files_dir)

            if not _exists(self.plant_files_2017_1_dir):
                os.makedirs(self.plant_files_2017_1_dir)

            self._field_boundaries_geojson = None
            self._field_boundaries_source_filename = None
            self._field_id_key = None
            self._rotation_schedule_tsv = None
            self._crop_kv_lookup_tsv = None
            self._sub_field_min_area_threshold_m2 = 0.0  # threshold in m2 for defining sub-field in peridot
            
            self._field_n = 0
            self._sub_field_n = 0
            self._sub_field_fp_n = 0

            self._geojson_hash = None
            self._geojson_timestamp = None
            self._geojson_is_valid = False
            self._field_columns = []
            self._valid_plant_files = []
            self._invalid_plant_files = []
            self._plant_file_provenance = {}
            self._subfields_source_signature = None
            self._wepp_source_signature = None
            self._wepp_bin = self.config_get_str('ag_fields', 'bin')
            self._watershed_integration_source_signature = None
            self._watershed_integration_summary = None
            self._watershed_integration_status = 'not_run'
            self._watershed_integration_error = None

    @property
    def field_n(self) -> int:
        return int(getattr(self, '_field_n', 0))

    @property
    def sub_field_n(self) -> int:
        return int(getattr(self, '_sub_field_n', 0))

    @property
    def sub_field_fp_n(self) -> int:
        return int(getattr(self, '_sub_field_fp_n', 0))

    @property
    def wepp_bin(self) -> Optional[str]:
        value = getattr(self, '_wepp_bin', None)
        if value:
            return str(value)
        return self.wepp_instance.wepp_bin

    @wepp_bin.setter
    @nodb_setter
    def wepp_bin(self, value: str) -> None:
        normalized = str(value).strip()
        if normalized not in get_linux_wepp_bin_opts():
            raise ValueError(f'Unknown WEPP executable: {normalized}')
        self._wepp_bin = normalized

    @property
    def geojson_timestamp(self) -> Optional[int]:
        return getattr(self, '_geojson_timestamp', None)

    @property
    def geojson_is_valid(self) -> bool:
        return bool(getattr(self, '_geojson_is_valid', False))

    @property
    def geojson_hash(self) -> Optional[str]:
        return getattr(self, '_geojson_hash', None)

    @property
    def field_columns(self) -> List[str]:
        return deepcopy(getattr(self, '_field_columns', []))
    
    @property
    def field_boundaries_geojson(self) -> Optional[str]:
        return getattr(self, '_field_boundaries_geojson', None)

    @property
    def field_boundaries_source_filename(self) -> Optional[str]:
        return getattr(self, '_field_boundaries_source_filename', None)

    @property
    def field_id_key(self) -> Optional[str]:
        return getattr(self, '_field_id_key', None)

    def validate_field_boundary_geojson(
        self,
        fn: str | os.PathLike[str],
        *,
        source_filename: Optional[str] = None,
    ) -> Dict[str, List[Any]]:
        """
        Validate a user-supplied field boundary GeoJSON and normalize it into the canonical
        `ag_fields/fields.WGS.geojson` location for downstream tooling.
        """
        candidate = Path(fn)
        search_paths = []
        if candidate.is_absolute():
            search_paths.append(candidate)
        else:
            search_paths.append(Path(self.ag_fields_dir) / candidate)
            search_paths.append(Path(self.wd) / candidate)

        source_path = next((p for p in search_paths if p.exists()), None)
        if source_path is None:
            raise FileNotFoundError(f'Field boundary geojson file not found: {search_paths[0]}')

        source_basename = PurePosixPath(str(source_filename or '').replace('\\', '/')).name.strip()
        if not source_basename:
            source_basename = source_path.name

        canonical_name = "fields.WGS.geojson"
        canonical_path = Path(self.ag_fields_dir) / canonical_name
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        geojson_fd, staged_geojson = tempfile.mkstemp(
            prefix='.field-boundaries-',
            suffix='.geojson',
            dir=self.ag_fields_dir,
        )
        parquet_fd, staged_parquet = tempfile.mkstemp(
            prefix='.rotation-schedule-',
            suffix='.parquet',
            dir=self.ag_fields_dir,
        )
        os.close(geojson_fd)
        os.close(parquet_fd)

        try:
            try:
                shutil.copy2(source_path, staged_geojson)
            except OSError as exc:
                raise OSError(f"Failed to stage field boundary GeoJSON: {exc}") from exc

            import geopandas as gpd

            df = gpd.read_file(staged_geojson, ignore_geometry=True)
            if "field_id" not in df.columns:
                raise ValueError(f'field_id column not found in field boundary GeoJSON: {source_path}')

            duplicates: Set[Any] = set()
            if df["field_id"].duplicated().any():
                duplicates = set(df[df["field_id"].duplicated()]["field_id"].tolist())
                self.logger.warning(
                    "Duplicate field_id values found in field boundary GeoJSON: %s", sorted(duplicates)
                )

            df.to_parquet(staged_parquet, index=False)
            geojson_hash = self._file_sha1(staged_geojson)

            with self.locked():
                os.replace(staged_geojson, canonical_path)
                os.replace(staged_parquet, self.rotation_schedule_parquet)
                self._field_boundaries_geojson = canonical_name
                self._field_boundaries_source_filename = source_basename
                self._field_n = len(df)
                self._geojson_hash = geojson_hash
                self._geojson_timestamp = int(time.time())
                self._geojson_is_valid = True
                self._field_columns = [str(col) for col in df.columns]
                self._field_id_key = None
                self._rotation_accessor = None
        finally:
            for staged_path in (staged_geojson, staged_parquet):
                if os.path.exists(staged_path):
                    os.unlink(staged_path)

        if _update_catalog_entry is not None:
            try:
                relative_path = os.path.relpath(self.rotation_schedule_parquet, self.wd)
            except ValueError:
                relative_path = 'ag_fields'
            try:
                _update_catalog_entry(self.wd, relative_path)
            except Exception as exc:  # broad-except: optional catalog refresh must not reject a valid upload
                self.logger.warning("Failed to refresh catalog for rotation schedule: %s", exc)

        return dict(field_id_duplicates=sorted(duplicates))

    def get_unique_crops(self) -> Set[str]:
        """Return the distinct crop names referenced by the rotation schedule."""
        rotation_schedule_df = pd.read_parquet(self.rotation_schedule_parquet)
        unique_crops: Set[str] = set()
        for year in self._crop_year_iter():
            column_key = self.get_rotation_key(year)
            unique_crops.update(str(value) for value in rotation_schedule_df[column_key].unique())
        return unique_crops

    def validate_field_id_key(self, key: str) -> None:
        if not self.field_boundaries_geojson:
            raise ValueError("field_boundaries_geojson is not set. Call validate_field_boundary_geojson first.")

        if key not in self.field_columns:
            raise ValueError(f'field_id_key "{key}" not found in field boundary GeoJSON columns: {self.field_columns}')

    def set_field_id_key(self, key: str) -> None:
        self.validate_field_id_key(key)
        with self.locked():
            self._field_id_key = key

    def confirm_schema(self, field_id_key: str, rotation_accessor: str) -> None:
        """Validate both schema values before persisting either one."""
        with self.locked():
            self.validate_field_id_key(field_id_key)
            self.validate_rotation_accessor(rotation_accessor)
            self._field_id_key = field_id_key
            self._rotation_accessor = rotation_accessor

    @property
    def field_boundaries_tif(self) -> str:
        return _join(self.ag_fields_dir, 'field_boundaries.tif')
    
    def rasterize_field_boundaries_geojson(self) -> None:
        """
        Rasterizes the field boundaries GeoJSON file to a TIFF using the project's DEM as a template.
        The values in the raster correspond to the field IDs specified by self.field_id_key.
        """
        # ogr2ogr -f GeoJSON -t_srs EPSG:4325 field_boundaries.geojson CSB_2008_2024_Hangman_with_Crop_and_Performance.shp

        self.logger.info("Rasterizing field boundaries GeoJSON to TIFF...")

        # Ensure necessary properties are set before proceeding
        if not self.field_boundaries_geojson:
            raise ValueError("field_boundaries_geojson is not set. Call validate_field_boundary_geojson first.")
            
        if not self.field_id_key:
            raise ValueError("field_id_key is not set. Call validate_field_boundary_geojson first.")

        # file is in ag_fields_dir don't change 
        geojson_path = _join(self.ag_fields_dir, self.field_boundaries_geojson)
        template_filepath = self.ron_instance.dem_fn
        output_filepath = self.field_boundaries_tif

        def _bounds_intersect(bounds_a, bounds_b):
            return not (
                bounds_a[2] <= bounds_b[0]
                or bounds_a[0] >= bounds_b[2]
                or bounds_a[3] <= bounds_b[1]
                or bounds_a[1] >= bounds_b[3]
            )

        # Verify that the input files exist
        if not _exists(template_filepath):
            raise FileNotFoundError(f'DEM file not found: {template_filepath}')
        if not _exists(geojson_path):
            raise FileNotFoundError(f'Field boundary GeoJSON file not found: {geojson_path}')

        # Import necessary libraries
        try:
            import geopandas as gpd
            import rasterio
            from rasterio.features import rasterize
        except ImportError:
            self.logger.error("This function requires geopandas and rasterio. Please install them.")
            raise

        # Read the vector data
        gdf = gpd.read_file(geojson_path)

        if gdf.empty:
            raise ValueError(f'Field boundary GeoJSON "{geojson_path}" does not contain any features.')

        # Drop features that lack usable geometry so rasterization does not silently fail.
        gdf = gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty]
        if gdf.empty:
            raise ValueError(f'Field boundary GeoJSON "{geojson_path}" does not contain any valid geometries.')

        # Check for duplicate field IDs and warn the user, as requested
        if gdf[self.field_id_key].duplicated().any():
            duplicates = gdf[gdf[self.field_id_key].duplicated()][self.field_id_key].tolist()
            self.logger.warning(f'Duplicate values found for field_id_key "{self.field_id_key}": {set(duplicates)}')

        # Open the template DEM to get its metadata (CRS, transform, dimensions)
        with rasterio.open(template_filepath) as src:
            meta = src.meta.copy()
            template_crs = src.crs
            template_bounds = src.bounds

            if template_crs is None:
                raise ValueError(f'DEM "{template_filepath}" lacks a coordinate reference system; unable to rasterize fields.')

            template_bounds_tuple = (
                float(template_bounds.left),
                float(template_bounds.bottom),
                float(template_bounds.right),
                float(template_bounds.top),
            )
            payload = json.loads(Path(geojson_path).read_text(encoding='utf-8'))
            payload_declares_crs = bool(payload.get('crs'))
            if gdf.crs is None or not payload_declares_crs:
                crs_inference = infer_geojson_crs(
                    payload,
                    explicit_crs=None,
                    project_crs=str(template_crs),
                    configured_crs=str(gdf.crs or "EPSG:4326"),
                    project_bounds=template_bounds_tuple,
                )
                if (
                    gdf.crs is None
                    or crs_inference.source == 'inferred_project_utm_coordinates'
                ):
                    gdf = gdf.set_crs(crs_inference.crs, allow_override=True)
                    self.logger.info(
                        'Field boundary GeoJSON lacks explicit CRS metadata; using %s (%s).',
                        crs_inference.crs,
                        crs_inference.source,
                    )

            original_bounds = gdf.total_bounds
            has_nonzero_field_ids = bool((gdf[self.field_id_key] != 0).any())

            if gdf.crs != template_crs:
                self.logger.info(
                    'Reprojecting field boundary geometry from %s to %s for rasterization.',
                    gdf.crs,
                    template_crs,
                )
                reprojected_gdf = gdf.to_crs(template_crs)
                reprojected_bounds = reprojected_gdf.total_bounds

                intersects_after = _bounds_intersect(reprojected_bounds, template_bounds)
                intersects_before = _bounds_intersect(original_bounds, template_bounds)

                if not intersects_after and intersects_before:
                    self.logger.warning(
                        'Field boundary features overlap the DEM grid before reprojection but not after. '
                        'Assuming the GeoJSON coordinates already match the DEM CRS and overriding the declared CRS.'
                    )
                    gdf = gdf.copy()
                    gdf = gdf.set_crs(template_crs, allow_override=True)
                else:
                    gdf = reprojected_gdf

            # Update metadata for the new output raster
            # Field IDs are integers, so we set dtype to int32.
            # nodata=0 means pixels outside the fields will have a value of 0.
            meta.update(compress='lzw', dtype=rasterio.int32, nodata=0)

        if not _bounds_intersect(gdf.total_bounds, template_bounds):
            raw_bounds = tuple(round(float(value), 3) for value in original_bounds)
            project_bounds = tuple(round(float(value), 3) for value in template_bounds_tuple)
            raise ValueError(
                'Field boundary geometries do not overlap the DEM extent after reprojection. '
                f'The project DEM uses {template_crs} with bounds {project_bounds}; '
                f'the uploaded boundary coordinate bounds are {raw_bounds}. '
                f'For best precision, export the boundaries in the project CRS ({template_crs}), '
                'or include correct CRS metadata when using another projected CRS.'
            )

        # Prepare shapes for rasterization. This creates a generator of (geometry, value) tuples.
        shapes = ((geom, value) for geom, value in zip(gdf.geometry, gdf[self.field_id_key]))

        # Create the new raster file and write the rasterized data
        with rasterio.open(output_filepath, 'w', **meta) as out:
            burned_array = rasterize(
                shapes=shapes,
                out_shape=(meta['height'], meta['width']),
                transform=meta['transform'],
                fill=0,  # This is the background value for pixels not covered by a polygon
                dtype=rasterio.int32
            )

            if not burned_array.any() and has_nonzero_field_ids:
                raise ValueError(
                    'Rasterization produced no field pixels. Ensure the field boundaries overlap the DEM '
                    'and that the GeoJSON CRS is declared correctly.'
                )

            # Write the resulting array to the first band of the output raster
            out.write(burned_array, 1)

        # read back the raster and verify the number of unique field IDs
        with rasterio.open(output_filepath) as src:
            data = src.read(1)
            unique_field_id_count = len(set(data[data != 0].flatten()))  # Exclude nodata (0) values  

        self.logger.info(f"Terminating Rasterization. Wrote {unique_field_id_count} objects to raster")

    @property
    def sub_field_min_area_threshold_m2(self) -> float:
        return float(getattr(self, '_sub_field_min_area_threshold_m2', 0.0))
    
    @sub_field_min_area_threshold_m2.setter
    @nodb_setter
    def sub_field_min_area_threshold_m2(self, value: float) -> None:
        if value < 0.0:
            raise ValueError('sub_field_min_area_threshold_m2 must be non-negative.')
        self._sub_field_min_area_threshold_m2 = float(value)

    def periodot_abstract_sub_fields(
        self,
        sub_field_min_area_threshold_m2: Optional[float] = None,
        verbose: bool = True
    ) -> None:
        """
        Run PERIDOT to abstract sub-fields (e.g. generate slope files) and post-process the results.
        """
        if sub_field_min_area_threshold_m2 is not None:
            self.sub_field_min_area_threshold_m2 = sub_field_min_area_threshold_m2
        
        watershed = Watershed.getInstance(self.wd)
        clip_hillslopes = watershed.clip_hillslopes
        clip_hillslope_length = watershed.clip_hillslope_length

        with self.locked():
            run_peridot_wbt_sub_fields_abstraction(
                self.wd,
                clip_hillslopes=clip_hillslopes,
                clip_hillslope_length=clip_hillslope_length,
                sub_field_min_area_threshold_m2=self.sub_field_min_area_threshold_m2,
                verbose=verbose
            )
            self._sub_field_n, self._sub_field_fp_n = post_abstract_sub_fields(self.wd, verbose=verbose)

    def get_sub_field_translator(self) -> Dict[str, Tuple[int, int, int]]:
        """
        returns a lookup dict of sub_field_id -> (field_id, topaz_id, wepp_id)
        """
        sub_field_translator = {}

        subfields_df = self.subfields_parquet

        for index, field in subfields_df.iterrows():
            field_id = field['field_id']
            topaz_id = str(field['topaz_id'])
            wepp_id = field['wepp_id']
            sub_field_id = field['sub_field_id']
            sub_field_translator[str(sub_field_id)] = (int(field_id), int(topaz_id), int(wepp_id))

        return sub_field_translator
    
    @property
    def sub_fields_map(self) -> str:
        return _join(self.ag_fields_dir, 'sub_fields/sub_field_id_map.tif')

    @property
    def sub_fields_geojson(self) -> str:
        return _join(self.ag_fields_dir, 'sub_fields/sub_fields.geojson')

    @property
    def sub_fields_wgs_geojson(self) -> str:
        return _join(self.ag_fields_dir, 'sub_fields/sub_fields.WGS.geojson')

    def polygonize_sub_fields(self) -> None:
        """
        polygonize sub fields
        """
        from .polygonize_sub_fields import polygonize_sub_fields

        polygonize_sub_fields(
            self.sub_fields_map, 
            self.get_sub_field_translator(),
            self.sub_fields_geojson)
        with self.locked():
            self._subfields_source_signature = self._schema_signature()

    @property
    def rotation_schedule_parquet(self) -> str:
        return _join(self.ag_fields_dir, 'rotation_schedule.parquet')

    @property
    def ag_field_wepp_runs_dir(self) -> str:
        return _join(self.wd, 'wepp/ag_fields/runs')

    @property
    def ag_field_wepp_output_dir(self) -> str:
        return _join(self.wd, 'wepp/ag_fields/output')

    @property
    def ag_fields_dir(self) -> str:
        return _join(self.wd, 'ag_fields')

    @property
    def ag_field_watershed_root(self) -> str:
        return _join(self.wd, 'wepp/ag_fields/watershed')

    @property
    def ag_field_watershed_runs_dir(self) -> str:
        return _join(self.ag_field_watershed_root, 'runs')

    @property
    def ag_field_watershed_output_dir(self) -> str:
        return _join(self.ag_field_watershed_root, 'output')

    @property
    def ag_field_watershed_manifest_dir(self) -> str:
        return _join(self.ag_field_watershed_root, 'manifest')

    @property
    def plant_files_dir(self) -> str:
        return _join(self.ag_fields_dir, 'plant_files')

    @property
    def plant_files_2017_1_dir(self) -> str:
        return _join(self.plant_files_dir, '2017.1')

    def clear_ag_field_wepp_runs(self) -> None:
        with self.locked():
            if _exists(self.ag_field_wepp_runs_dir):
                shutil.rmtree(self.ag_field_wepp_runs_dir)
            os.makedirs(self.ag_field_wepp_runs_dir, exist_ok=True)
            self._wepp_source_signature = None

    def clear_ag_field_wepp_outputs(self) -> None:
        with self.locked():
            if _exists(self.ag_field_wepp_output_dir):
                shutil.rmtree(self.ag_field_wepp_output_dir)
            os.makedirs(self.ag_field_wepp_output_dir, exist_ok=True)
            self._wepp_source_signature = None

    def clear_ag_field_wepp_artifacts(self) -> None:
        with self.locked():
            for directory in (self.ag_field_wepp_runs_dir, self.ag_field_wepp_output_dir):
                if _exists(directory):
                    shutil.rmtree(directory)
                os.makedirs(directory, exist_ok=True)
            self._wepp_source_signature = None

    def run_watershed_integration(
        self,
        max_workers: Optional[int] = None,
        phase_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Run the isolated Concept 2 watershed integration."""
        from .watershed_integration import AgFieldsWatershedIntegrator

        started_at = int(time.time())
        with self.locked():
            current_status = str(getattr(self, '_watershed_integration_status', 'not_run'))
            if current_status == 'running' or current_status.startswith('running:'):
                raise AgFieldsNoDbLockedException('AgFields watershed integration is already running.')
            self._watershed_integration_status = 'running:preflight'
            self._watershed_integration_source_signature = None
            self._watershed_integration_summary = None
            self._watershed_integration_error = None

        def update_phase(phase: str) -> None:
            with self.locked():
                self._watershed_integration_status = f'running:{phase}'
            if phase_callback is not None:
                phase_callback(phase)

        integrator = AgFieldsWatershedIntegrator(
            self,
            max_workers=max_workers,
            phase_callback=update_phase,
        )
        try:
            summary = integrator.run()
        except Exception as exc:  # broad-except: persisted public operation boundary
            public_message = str(exc).replace(str(Path(self.wd).resolve()), '<run>')
            failure = {
                'phase': integrator.phase,
                'type': type(exc).__name__,
                'message': public_message,
                'failed_at': int(time.time()),
                'started_at': started_at,
            }
            with self.locked():
                self._watershed_integration_status = 'failed'
                self._watershed_integration_error = failure
                self._watershed_integration_summary = None
            raise

        with self.locked():
            self._watershed_integration_source_signature = summary['source_signature']
            self._watershed_integration_summary = summary
            self._watershed_integration_status = 'completed'
            self._watershed_integration_error = None
        return deepcopy(summary)

    def clear_watershed_integration(self) -> None:
        """Clear only the fixed isolated Concept 2 subtree and additive state."""
        root = Path(self.ag_field_watershed_root)
        expected = Path(self.wd).resolve() / 'wepp' / 'ag_fields' / 'watershed'
        if root.absolute() != expected.absolute():
            raise ValueError('AgFields watershed path does not match the fixed isolated root.')
        if any(path.is_symlink() for path in (expected.parent.parent, expected.parent, expected)):
            raise ValueError('Refusing to clear through a symlinked AgFields watershed path.')
        with self.locked():
            current_status = str(getattr(self, '_watershed_integration_status', 'not_run'))
            if current_status == 'running' or current_status.startswith('running:'):
                raise AgFieldsNoDbLockedException('AgFields watershed integration is running.')
            self._watershed_integration_status = 'clearing'
        try:
            if root.exists():
                shutil.rmtree(root)
        except OSError as exc:
            with self.locked():
                self._watershed_integration_status = 'failed'
                self._watershed_integration_error = {
                    'phase': 'clear',
                    'type': type(exc).__name__,
                    'message': str(exc).replace(str(Path(self.wd).resolve()), '<run>'),
                    'failed_at': int(time.time()),
                }
            raise
        with self.locked():
            self._watershed_integration_source_signature = None
            self._watershed_integration_summary = None
            self._watershed_integration_status = 'not_run'
            self._watershed_integration_error = None

    def get_watershed_integration_state(self) -> Dict[str, Any]:
        """Return additive state, including historical-payload defaults."""
        summary = deepcopy(getattr(self, '_watershed_integration_summary', None))
        status = str(getattr(self, '_watershed_integration_status', 'not_run'))
        artifacts_exist = Path(self.ag_field_watershed_manifest_dir, 'integration_summary.json').is_file()
        stage4_signature = getattr(self, '_wepp_source_signature', None)
        stored_stage4_signature = summary.get('stage4_source_signature') if summary else None
        upstream_changed = False
        if summary and summary.get('upstream_timestamps'):
            prep = RedisPrep.tryGetInstance(self.wd)
            if prep is not None:
                upstream_changed = any(
                    prep[str(task)] != stored
                    for task, stored in (
                        (TaskEnum.abstract_watershed, summary['upstream_timestamps'].get(str(TaskEnum.abstract_watershed))),
                        (TaskEnum.build_landuse, summary['upstream_timestamps'].get(str(TaskEnum.build_landuse))),
                        (TaskEnum.build_soils, summary['upstream_timestamps'].get(str(TaskEnum.build_soils))),
                        (TaskEnum.build_climate, summary['upstream_timestamps'].get(str(TaskEnum.build_climate))),
                        (TaskEnum.run_wepp_hillslopes, summary['upstream_timestamps'].get(str(TaskEnum.run_wepp_hillslopes))),
                        (TaskEnum.run_ag_fields, summary['upstream_timestamps'].get(str(TaskEnum.run_ag_fields))),
                    )
                )
        stale = bool(summary) and (
            not artifacts_exist
            or self.get_staleness()['wepp_runs']
            or upstream_changed
            or (stored_stage4_signature is not None and stored_stage4_signature != stage4_signature)
        )
        return {
            'status': status,
            'stale': stale,
            'source_signature': getattr(self, '_watershed_integration_source_signature', None),
            'summary': summary,
            'error': deepcopy(getattr(self, '_watershed_integration_error', None)),
            'root_relpath': 'wepp/ag_fields/watershed',
            'browse_relpath': 'wepp/ag_fields/watershed/',
            'limitation': (
                'Field water and sediment are injected at the parent outlet; downslope '
                'buffer, trapping, and runon effects are not represented.'
            ),
        }

    @property
    def rotation_accessor(self) -> Optional[str]:
        return getattr(self, '_rotation_accessor', None)

    @staticmethod
    def _parse_year_bound(value: Any, field_name: str) -> int:
        if isinstance(value, bool):
            raise ValueError(f'{field_name} must be an integer year, got {value!r}.')
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(f'{field_name} must be an integer year, got {value!r}.')
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{field_name} must be an integer year, got {value!r}.') from exc

    def _observed_year_bounds(self) -> Tuple[int, int]:
        climate = self.climate_instance
        start_year = self._parse_year_bound(climate.observed_start_year, 'observed_start_year')
        end_year = self._parse_year_bound(climate.observed_end_year, 'observed_end_year')
        if end_year < start_year:
            raise ValueError('observed_end_year must be greater than or equal to observed_start_year.')
        return start_year, end_year

    def validate_rotation_accessor(self, candidate: str) -> None:
        """
        Validate the column accessor used to read the rotation schedule.
        Must contain {} str.format is applied with year as the argument.
        """
        if '{}' not in candidate:
            self.logger.error("rotation_accessor must contain '{}' for year substitution.")
            raise ValueError("rotation_accessor must contain '{}' for year substitution.")

        start_year, end_year = self._observed_year_bounds()

        for year in range(start_year, end_year + 1):
            column_key = candidate.format(str(year))

            if column_key not in self.field_columns:
                self.logger.error(f'Column key "{column_key}" not found in field boundary GeoJSON columns: {self.field_columns}')
                raise ValueError(f'Column key "{column_key}" not found in field boundary GeoJSON columns: {self.field_columns}')

    def set_rotation_accessor(self, candidate: str) -> None:
        self.logger.info(f'set_rotation_accessor("{candidate}")')
        self.validate_rotation_accessor(candidate)
        with self.locked():
            self._rotation_accessor = candidate
            self.logger.info(f'Set rotation_accessor to "{candidate}"')

    @staticmethod
    def _normalized_plant_filename(filename: str) -> str:
        path = PurePosixPath(filename)
        stem = Path(path.name).stem.replace(' ', '_')
        return f'{stem}.man'

    @staticmethod
    def _unique_archive_filename(filename: str, assigned: Set[str]) -> str:
        candidate = filename
        stem = Path(filename).stem
        counter = 1
        while candidate.casefold() in assigned:
            candidate = f'{stem}_{counter}.man'
            counter += 1
        assigned.add(candidate.casefold())
        return candidate

    def _persist_plant_processing_failure(self, filename: str, message: str) -> None:
        invalid = [
            item for item in getattr(self, '_invalid_plant_files', [])
            if item.get('filename') != filename
        ]
        invalid.append({'filename': filename, 'error': message})
        with self.locked():
            self._invalid_plant_files = sorted(invalid, key=lambda item: item['filename'].casefold())

    @staticmethod
    def _normalize_applied_residue_hmax(management: Any) -> List[Dict[str, Any]]:
        residue_plant_names: Set[str] = set()
        active_plant_names: Set[str] = set()

        for operation in getattr(management, 'ops', ()):
            data = getattr(operation, 'data', None)
            residue_ref = getattr(data, 'iresad', None)
            if (
                getattr(operation, 'landuse', None) == 1
                and getattr(data, 'pcode', None) in (10, 12)
                and isinstance(residue_ref, ScenarioReference)
                and residue_ref.loop_name
            ):
                residue_plant_names.add(residue_ref.loop_name)

        for initial in getattr(management, 'inis', ()):
            plant_ref = getattr(getattr(initial, 'data', None), 'iresd', None)
            if isinstance(plant_ref, ScenarioReference) and plant_ref.loop_name:
                active_plant_names.add(plant_ref.loop_name)

        for year in getattr(management, 'years', ()):
            plant_ref = getattr(getattr(year, 'data', None), 'itype', None)
            if isinstance(plant_ref, ScenarioReference) and plant_ref.loop_name:
                active_plant_names.add(plant_ref.loop_name)

        normalizations: List[Dict[str, Any]] = []
        for plant in getattr(management, 'plants', ()):
            if plant.name not in residue_plant_names or plant.name in active_plant_names:
                continue
            hmax = getattr(getattr(plant, 'data', None), 'hmax', None)
            if not isinstance(hmax, (int, float)) or not hmax <= 0:
                continue
            plant.data.hmax = _APPLIED_RESIDUE_HMAX_FLOOR_M
            normalizations.append(
                {
                    'scenario': plant.name,
                    'field': 'plant.data.hmax',
                    'original_value': float(hmax),
                    'normalized_value': _APPLIED_RESIDUE_HMAX_FLOOR_M,
                    'units': 'm',
                    'reason': _APPLIED_RESIDUE_HMAX_REASON,
                }
            )

        return normalizations

    @staticmethod
    def _rewrite_management_preserving_header_comments(
        management: Any,
        path: Path,
    ) -> None:
        source_lines = path.read_text(encoding='utf-8').splitlines()
        header_lines: List[str] = []
        for line in source_lines[1:]:
            if line.lstrip().startswith('#') or not line.strip():
                header_lines.append(line)
                continue
            break

        rendered_lines = str(management).splitlines()
        if header_lines:
            rendered_lines = [rendered_lines[0], *header_lines, *rendered_lines[1:]]
        path.write_text('\n'.join(rendered_lines) + '\n', encoding='utf-8', newline='\n')

    def handle_plant_file_db_upload(self, plant_db_zip_fn: str) -> Dict[str, Any]:
        """
        Unzip the plant file database zip files int self.plant_files_dir.
        
        The zip file should contain .man files
        
        - Normalizes file names by removing spaces and converting to underscores
        - Automatically downgrades 2017.1 plant files to 98.4
        """
        self.logger.info(f'handle_plant_file_db_upload("{plant_db_zip_fn}")')
        
        root = Path(self.ag_fields_dir).resolve()
        zip_path = (root / plant_db_zip_fn).resolve()
        if root not in zip_path.parents or not zip_path.is_file():
            raise FileNotFoundError(f'Plant file DB zip not found inside ag_fields: {plant_db_zip_fn}')

        assigned: Set[str] = set()
        staged: List[Dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix='.plant-upload-', dir=self.ag_fields_dir) as staging_dir:
            staging = Path(staging_dir)
            final_staging = staging / 'final'
            source_staging = staging / '2017.1'
            final_staging.mkdir()
            source_staging.mkdir()

            with self.timed('Extracting .man files from plant file DB zip'):
                with zipfile.ZipFile(zip_path, 'r') as archive:
                    for file_info in archive.infolist():
                        path_in_zip = PurePosixPath(file_info.filename)
                        if path_in_zip.suffix.lower() != '.man':
                            continue
                        if path_in_zip.is_absolute() or '..' in path_in_zip.parts:
                            self.logger.warning('Skipping plant file with unsafe path: %s', file_info.filename)
                            continue

                        normalized = self._unique_archive_filename(
                            self._normalized_plant_filename(path_in_zip.name), assigned
                        )
                        with archive.open(file_info) as source:
                            first_line = source.readline()
                            is_2017_1 = b'2017.1' in first_line
                            target = (source_staging if is_2017_1 else final_staging) / normalized
                            with target.open('wb') as destination:
                                destination.write(first_line)
                                shutil.copyfileobj(source, destination, length=64 * 1024)
                        staged.append(
                            {
                                'filename': normalized,
                                'source_filename': file_info.filename,
                                'is_2017_1': is_2017_1,
                            }
                        )

            with self.timed('Downgrading 2017.1 plant files to 98.4 format'):
                for item in staged:
                    if not item['is_2017_1']:
                        continue
                    filename = item['filename']
                    try:
                        management = read_management(str(source_staging / filename))
                        item['normalizations'] = self._normalize_applied_residue_hmax(management)
                        downgrade_to_98_4_format(
                            management,
                            str(final_staging / filename),
                            first_year_only=False,
                        )
                    except (OSError, UnicodeError, ValueError, AssertionError, IndexError) as exc:
                        message = str(exc) or exc.__class__.__name__
                        self._persist_plant_processing_failure(filename, message)
                        raise PlantFileProcessingError(filename, message) from exc

            staged_valid: Set[str] = set()
            staged_errors: Dict[str, str] = {}
            staged_by_filename = {item['filename']: item for item in staged}
            for path in sorted(final_staging.glob('*.man'), key=lambda item: item.name.casefold()):
                try:
                    management = read_management(str(path))
                    item = staged_by_filename[path.name]
                    if not item['is_2017_1']:
                        item['normalizations'] = self._normalize_applied_residue_hmax(management)
                        if item['normalizations']:
                            self._rewrite_management_preserving_header_comments(management, path)
                except (OSError, UnicodeError, ValueError, AssertionError, IndexError) as exc:
                    staged_errors[path.name] = str(exc) or exc.__class__.__name__
                else:
                    staged_valid.add(path.name)

            replaced: List[str] = []
            provenance = deepcopy(getattr(self, '_plant_file_provenance', {}))
            with self.locked():
                for item in staged:
                    filename = item['filename']
                    final_target = Path(self.plant_files_dir) / filename
                    if final_target.exists():
                        replaced.append(filename)
                    os.replace(final_staging / filename, final_target)
                    source_target = Path(self.plant_files_2017_1_dir) / filename
                    if item['is_2017_1']:
                        os.replace(source_staging / filename, source_target)
                    elif source_target.exists():
                        source_target.unlink()
                    provenance[filename] = {
                        'source_filename': item['source_filename'],
                        'format': '2017.1_downgraded' if item['is_2017_1'] else '98.4',
                        'replaced': filename in replaced,
                        'normalizations': deepcopy(item.get('normalizations', [])),
                    }

                all_valid: List[str] = []
                all_invalid: List[Dict[str, str]] = []
                for path in sorted(Path(self.plant_files_dir).glob('*.man'), key=lambda item: item.name.casefold()):
                    if path.name in staged_errors:
                        all_invalid.append({'filename': path.name, 'error': staged_errors[path.name]})
                        continue
                    if path.name in staged_valid:
                        all_valid.append(path.name)
                        continue
                    try:
                        read_management(str(path))
                    except (OSError, UnicodeError, ValueError, AssertionError, IndexError) as exc:
                        all_invalid.append({'filename': path.name, 'error': str(exc) or exc.__class__.__name__})
                    else:
                        all_valid.append(path.name)
                self._valid_plant_files = all_valid
                self._invalid_plant_files = all_invalid
                self._plant_file_provenance = provenance

        inventory = self.get_plant_file_inventory()
        inventory['replaced'] = sorted(replaced, key=str.casefold)
        self.logger.info('Finished handling plant file DB upload for %s', plant_db_zip_fn)
        return inventory

    def get_valid_plant_files(self) -> List[str]:
        return deepcopy(getattr(self, '_valid_plant_files', []))

    def get_invalid_plant_files(self) -> List[Dict[str, str]]:
        return deepcopy(getattr(self, '_invalid_plant_files', []))

    def get_plant_file_inventory(self) -> Dict[str, Any]:
        valid = self.get_valid_plant_files()
        invalid = self.get_invalid_plant_files()
        provenance = deepcopy(getattr(self, '_plant_file_provenance', {}))
        invalid_by_name = {item['filename']: item['error'] for item in invalid}
        filenames = sorted(set(valid) | set(invalid_by_name), key=str.casefold)
        files = []
        for filename in filenames:
            source = provenance.get(filename, {})
            files.append(
                {
                    'filename': filename,
                    'valid': filename in valid,
                    'error': invalid_by_name.get(filename),
                    'format': source.get('format', '98.4'),
                    'source_filename': source.get('source_filename', filename),
                    'replaced': bool(source.get('replaced', False)),
                    'normalizations': deepcopy(source.get('normalizations', [])),
                }
            )
        return {'files': files, 'valid_files': valid, 'invalid_files': invalid}

    def delete_plant_file(self, filename: str) -> Dict[str, Any]:
        if not filename or Path(filename).name != filename or Path(filename).suffix.lower() != '.man':
            raise ValueError('filename must be a .man basename without path components.')
        canonical = self._normalized_plant_filename(filename)
        with self.locked():
            for directory in (self.plant_files_dir, self.plant_files_2017_1_dir):
                path = Path(directory) / canonical
                if path.exists():
                    path.unlink()
            self._valid_plant_files = [name for name in self.get_valid_plant_files() if name != canonical]
            self._invalid_plant_files = [
                item for item in self.get_invalid_plant_files() if item.get('filename') != canonical
            ]
            provenance = deepcopy(getattr(self, '_plant_file_provenance', {}))
            provenance.pop(canonical, None)
            self._plant_file_provenance = provenance
        return self.get_plant_file_inventory()

    def get_rotation_key(self, year: int) -> str:  # to access Crop{year} column in rotation_schedule_parquet
        if self.rotation_accessor is None:
            raise ValueError('rotation_accessor is not set. Call set_rotation_accessor first.')
        return self.rotation_accessor.format(str(year))

    def _crop_year_iter(self) -> Iterator[int]:
        start_year, end_year = self._observed_year_bounds()
        for year in range(start_year, end_year + 1):
            yield year

    @property
    def rotation_lookup_path(self) -> str:
        return _join(self.ag_fields_dir, 'rotation_lookup.tsv')

    def _validate_rotation_rows(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        row_list = list(rows)
        by_crop: Dict[str, Dict[str, Any]] = {}
        duplicates: Set[str] = set()
        for row in row_list:
            crop_name = str(row.get('crop_name', '')).strip()
            if crop_name in by_crop:
                duplicates.add(crop_name)
            by_crop[crop_name] = row

        try:
            expected_crops = self.get_unique_crops()
        except (FileNotFoundError, KeyError, ValueError):
            expected_crops = set()

        results: List[Dict[str, Any]] = []
        for crop_name in sorted(expected_crops | set(by_crop), key=str.casefold):
            row = by_crop.get(crop_name)
            used = crop_name in expected_crops
            if row is None:
                results.append(
                    {
                        'crop_name': crop_name,
                        'database': None,
                        'rotation_id': None,
                        'status': 'unmapped',
                        'valid': False,
                        'message': 'Crop is not mapped.',
                        'used': used,
                    }
                )
                continue

            database = str(row.get('database') or row.get('source') or '').strip()
            rotation_value = row.get('rotation_id', row.get('value'))
            rotation_id = str(rotation_value).strip() if rotation_value is not None else ''
            base_result = {
                'crop_name': crop_name,
                'database': database or None,
                'rotation_id': rotation_id or None,
                'used': used,
            }
            if not crop_name or '\t' in crop_name or '\n' in crop_name or '\r' in crop_name:
                results.append({**base_result, 'status': 'error', 'valid': False, 'message': 'crop_name is required and cannot contain tabs or newlines.'})
                continue
            if crop_name in duplicates:
                results.append({**base_result, 'status': 'error', 'valid': False, 'message': 'Duplicate crop mapping.'})
                continue
            if not database and not rotation_id:
                results.append({**base_result, 'status': 'unmapped', 'valid': False, 'message': 'Crop is not mapped.'})
                continue
            if not database or not rotation_id:
                results.append({**base_result, 'status': 'error', 'valid': False, 'message': 'Both database and rotation_id are required for a mapped crop.'})
                continue
            if any(token in rotation_id for token in ('\t', '\n', '\r')):
                results.append({**base_result, 'status': 'error', 'valid': False, 'message': 'rotation_id cannot contain tabs or newlines.'})
                continue
            try:
                rotation = CropRotationManager.resolve_rotation(
                    self.ag_fields_dir,
                    self.landuse_instance.mapping,
                    crop_name,
                    database,
                    rotation_id,
                    logger_name=self.logger.name,
                )
            except (ValueError, FileNotFoundError) as exc:
                results.append({**base_result, 'status': 'error', 'valid': False, 'message': str(exc)})
                continue
            results.append(
                {
                    **base_result,
                    'database': str(rotation.database),
                    'rotation_id': str(rotation.rotation_id),
                    'man_file_path': rotation.man_path,
                    'status': 'ok',
                    'valid': True,
                    'message': None,
                }
            )
        return results

    def validate_rotation_lookup(self) -> List[Dict[str, Any]]:
        self.logger.info('validate_rotation_lookup')
        rows: List[Dict[str, Any]] = []
        path = Path(self.rotation_lookup_path)
        if path.exists():
            with path.open(newline='', encoding='utf-8') as stream:
                reader = csv.DictReader(stream, delimiter='\t')
                if reader.fieldnames != ['crop_name', 'database', 'rotation_id']:
                    return [
                        {
                            'crop_name': '',
                            'database': None,
                            'rotation_id': None,
                            'status': 'error',
                            'valid': False,
                            'message': 'rotation_lookup.tsv must contain crop_name, database, and rotation_id columns.',
                            'used': False,
                        }
                    ]
                rows.extend(dict(row) for row in reader)
        return self._validate_rotation_rows(rows)

    def write_rotation_lookup(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        row_list = list(rows)
        results = self._validate_rotation_rows(row_list)
        errors = [result for result in results if result['status'] == 'error']
        if errors:
            raise RotationLookupValidationError(results)

        mapped = [result for result in results if result['status'] == 'ok']
        with self.locked():
            fd, temporary = tempfile.mkstemp(prefix='.rotation-lookup-', suffix='.tsv', dir=self.ag_fields_dir, text=True)
            try:
                with os.fdopen(fd, 'w', newline='', encoding='utf-8') as stream:
                    writer = csv.DictWriter(
                        stream,
                        fieldnames=['crop_name', 'database', 'rotation_id'],
                        delimiter='\t',
                        lineterminator='\n',
                    )
                    writer.writeheader()
                    for result in sorted(mapped, key=lambda item: item['crop_name'].casefold()):
                        writer.writerow(
                            {
                                'crop_name': result['crop_name'],
                                'database': result['database'],
                                'rotation_id': result['rotation_id'],
                            }
                        )
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.rotation_lookup_path)
                self._rotation_lookup_hash = self._file_sha1(self.rotation_lookup_path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return self.validate_rotation_lookup()

    def get_weppcloud_management_options(self) -> List[Dict[str, str]]:
        mapping = load_map(self.landuse_instance.mapping)
        options = [
            {'id': str(key), 'description': str(value.get('Description', ''))}
            for key, value in mapping.items()
        ]
        return sorted(options, key=lambda item: (int(item['id']) if isint(item['id']) else 10**12, item['id']))

    @staticmethod
    def _file_sha1(path: str | os.PathLike[str]) -> Optional[str]:
        candidate = Path(path)
        if not candidate.is_file():
            return None
        digest = hashlib.sha1()
        with candidate.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        return digest.hexdigest()

    def _schema_signature(self) -> Optional[str]:
        if not self.geojson_hash or not self.field_id_key or not self.rotation_accessor:
            return None
        payload = json.dumps(
            [self.geojson_hash, self.field_id_key, self.rotation_accessor],
            separators=(',', ':'),
        )
        return hashlib.sha1(payload.encode('utf-8')).hexdigest()

    def _workflow_signature(self) -> Optional[str]:
        source = getattr(self, '_subfields_source_signature', None)
        lookup_hash = self._file_sha1(self.rotation_lookup_path)
        if not source or not lookup_hash:
            return None
        return hashlib.sha1(f'{source}:{lookup_hash}'.encode('utf-8')).hexdigest()

    def get_staleness(self) -> Dict[str, bool]:
        subfields_exist = self.sub_field_n > 0 or Path(self.sub_fields_wgs_geojson).is_file()
        subfields_stale = subfields_exist and (
            self._schema_signature() != getattr(self, '_subfields_source_signature', None)
        )
        runs_path = Path(self.ag_field_wepp_runs_dir)
        outputs_path = Path(self.ag_field_wepp_output_dir)
        wepp_exists = any(runs_path.glob('p*.run')) or (
            outputs_path.is_dir() and any(outputs_path.iterdir())
        )
        wepp_stale = wepp_exists and (
            subfields_stale
            or self._workflow_signature() != getattr(self, '_wepp_source_signature', None)
        )
        return {'subfields': subfields_stale, 'wepp_runs': wepp_stale}

    def get_readiness(self) -> Dict[str, Any]:
        observed_modes = {
            ClimateMode.Observed,
            ClimateMode.ObservedPRISM,
            ClimateMode.ObservedDb,
            ClimateMode.PRISM,
            ClimateMode.EOBS,
            ClimateMode.AGDC,
            ClimateMode.GridMetPRISM,
            ClimateMode.DepNexrad,
        }
        try:
            start_year, end_year = self._observed_year_bounds()
            observed_ready = self.climate_instance.climate_mode in observed_modes
        except ValueError:
            start_year = None
            end_year = None
            observed_ready = False

        missing_parent_ids: List[int] = []
        if Path(self.subfields_parquet_path).is_file():
            parent_ids = sorted({int(value) for value in self.subfields_parquet['wepp_id'].tolist()})
            for wepp_id in parent_ids:
                runs_dir = Path(self.wd) / 'wepp' / 'runs'
                if not (runs_dir / f'p{wepp_id}.sol').is_file() or not (runs_dir / f'p{wepp_id}.cli').is_file():
                    missing_parent_ids.append(wepp_id)
            parent_wepp_ready = bool(parent_ids) and not missing_parent_ids
        else:
            parent_wepp_ready = False

        return {
            'observed_climate': observed_ready,
            'observed_start_year': start_year,
            'observed_end_year': end_year,
            'watershed_abstraction': (Path(self.wd) / 'dem' / 'wbt' / 'flovec.tif').is_file(),
            'parent_wepp': parent_wepp_ready,
            'missing_parent_wepp_ids': missing_parent_ids,
        }

    @property
    def subfields_parquet_path(self) -> str:
        return _join(self.ag_fields_dir, 'sub_fields/fields.parquet')

    @property
    def subfields_parquet(self) -> pd.DataFrame:
        if not _exists(self.subfields_parquet_path):
            raise FileNotFoundError(f'Sub-fields parquet file not found: {self.subfields_parquet_path}')
        return pd.read_parquet(self.subfields_parquet_path)

    def run_wepp_ag_fields(self, max_workers: Optional[int] = None) -> Dict[str, int]:
        """
        Run WEPP for each sub-field defined in the Peridot output.

        e.g. rotation_schedule_year_key_func = lambda year: f'Crop{year}'
        """
        self.logger.info('run_wepp_ag_fields()')
        start_year, end_year = self._observed_year_bounds()

        watershed = self.watershed_instance
        clip_hillslopes = watershed.clip_hillslopes
        clip_hillslope_length = watershed.clip_hillslope_length
        wepp_bin = self.wepp_bin

        subfields_df = self.subfields_parquet
        rotation_schedule_df = pd.read_parquet(self.rotation_schedule_parquet)

        tasks: List[Tuple[int, str, int, int, List[str]]] = []
        for index, field in subfields_df.iterrows():

            field_id = field['field_id']
            topaz_id = str(field['topaz_id'])
            wepp_id = field['wepp_id']
            sub_field_id = field['sub_field_id']

            self.logger.info(f'  Running WEPP for field_id={field_id}, topaz_id={topaz_id}, wepp_id={wepp_id}, sub_field_id={sub_field_id}')

            # find the field row in the rotation schedule and extract the crop rotation schedule
            field_rotation_schedule_row = rotation_schedule_df.loc[
                rotation_schedule_df[self.field_id_key] == field_id
            ]

            if field_rotation_schedule_row.empty:
                raise ValueError(f'No rotation row for {field_id}')

            # collapse the 1-row DataFrame to a plain dict
            field_rotation_schedule_row = field_rotation_schedule_row.iloc[0].to_dict()

            crop_rotation_schedule = []
            for year in range(start_year, end_year + 1):
                rotation_key_for_year = self.get_rotation_key(year)
                crop = field_rotation_schedule_row.get(rotation_key_for_year)
                if pd.isna(crop):
                    raise ValueError(f'No crop rotation for field {field_id}, year {year}')
                crop_rotation_schedule.append(str(crop))

            self.logger.info(f'    Crop rotation schedule: {crop_rotation_schedule}')
            tasks.append((field_id, topaz_id, wepp_id, sub_field_id, crop_rotation_schedule))

        total_tasks = len(tasks)
        if total_tasks == 0:
            self.logger.info('No sub-field records found; nothing to run.')
            return {'run_count': 0}

        cpu_count = os.cpu_count() or 1
        if max_workers is None:
            max_workers = min(total_tasks, cpu_count)
        if max_workers < 1:
            max_workers = 1
        if max_workers > max(cpu_count, 16):
            max_workers = max(cpu_count, 16)

        self.logger.info(f'Submitting {total_tasks} sub-field WEPP runs with max_workers={max_workers}')

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures: Dict[Future[None], Tuple[int, str, int, int]] = {}
            for field_id, topaz_id, wepp_id, sub_field_id, schedule in tasks:
                self.logger.info(
                    f'  Submitting sub_field_id={sub_field_id} (field_id={field_id}, topaz_id={topaz_id}, wepp_id={wepp_id})'
                )
                future = pool.submit(
                    run_wepp_subfield,
                    self.wd,
                    field_id,
                    topaz_id,
                    wepp_id,
                    sub_field_id,
                    schedule,
                    clip_hillslopes,
                    clip_hillslope_length,
                    wepp_bin,
                )
                futures[future] = (field_id, topaz_id, wepp_id, sub_field_id)

            completed = 0
            pending = set(futures.keys())
            while pending:
                done, pending = wait(pending, timeout=30, return_when=FIRST_COMPLETED)

                if not done:
                    self.logger.info('  Sub-field simulations still running after 30 seconds; continuing to wait.')
                    continue

                for future in done:
                    field_id, topaz_id, wepp_id, sub_field_id = futures[future]
                    try:
                        future.result()
                        completed += 1
                        self.logger.info(
                            f'  ({completed}/{total_tasks}) sub_field_id={sub_field_id} (field_id={field_id}, wepp_id={wepp_id}) completed.'
                        )
                    except Exception as exc:  # broad-except: concurrent sub-field task boundary
                        for remaining in pending:
                            remaining.cancel()
                        self.logger.error(
                            f'  Sub-field run failed (field_id={field_id}, topaz_id={topaz_id}, sub_field_id={sub_field_id}): {exc}'
                        )
                        raise AgFieldsRunError(field_id, sub_field_id, str(exc)) from exc

        with self.locked():
            self._wepp_source_signature = self._workflow_signature()
        return {'run_count': total_tasks}


class CropRotationDatabase(Enum):
    WEPP_CLOUD = 'weppcloud'
    PLANT_FILES_DB = 'plant_file_db'

    def __str__(self) -> str:
        return self.value

    def __getstate__(self) -> str:
        return self.value


class CropRotation:
    def __init__(self, crop_name: str, database: CropRotationDatabase, rotation_id: int | str, man_path: str):
        self.crop_name = crop_name
        self.database = database  # 'weppcloud' or 'plant_files'
        self.rotation_id = rotation_id  # dom key from the project's mapping or plant file name
        self.man_path = man_path  # path to management file

    def __repr__(self) -> str:
        return f'CropRotation(crop_name={self.crop_name}, database={self.database}, rotation_id={self.rotation_id}, man_path={self.man_path})'
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'crop_name': self.crop_name,
            'database': str(self.database),
            'value': self.rotation_id,
            'man_file_path': self.man_path,
        }

# Example output of rotation_manager.rotation_lookup
# {'Alfalfa': CropRotation(crop_name=Alfalfa, database=plant_file_db, rotation_id=alfalfa,spr_seeded,NT,_cm8-wepp.man, man_path=/wc1/runs/co/copacetic-note/ag_fields/plant_files/alfalfa,spr_seeded,NT,_cm8-wepp.man),
#  'Barley': CropRotation(crop_name=Barley, database=plant_file_db, rotation_id=barley,spr,MT,_cm8,_fchisel-wepp.man, man_path=/wc1/runs/co/copacetic-note/ag_fields/plant_files/barley,spr,MT,_cm8,_fchisel-wepp.man),
#  'Buckwheat': CropRotation(crop_name=Buckwheat, database=weppcloud, rotation_id=73, man_path=/workdir/wepppy/wepppy/wepp/management/data/GIS/Poor grass.man),
#  'Canola': CropRotation(crop_name=Canola, database=plant_file_db, rotation_id=canola,spr,MT,_cm8-wepp.man, man_path=/wc1/runs/co/copacetic-note/ag_fields/plant_files/canola,spr,MT,_cm8-wepp.man),
#  'Chick Peas': CropRotation(crop_name=Chick Peas, database=plant_file_db, rotation_id=chickpeas,spr,NT,_cm8-wepp.man, man_path=/wc1/runs/co/copacetic-note/ag_fields/plant_files/chickpeas,spr,NT,_cm8-wepp.man),
#  'Christmas Trees': CropRotation(crop_name=Christmas Trees, database=weppcloud, rotation_id=42, man_path=/workdir/wepppy/wepppy/wepp/management/data/UnDisturbed/Old_Forest.man),
#  'Clover/Wildflowers': CropRotation(crop_name=Clover/Wildflowers, database=weppcloud, rotation_id=73, man_path=/workdir/wepppy/wepppy/wepp/management/data/GIS/Poor grass.man),
#  'Deciduous Forest': CropRotation(crop_name=Deciduous Forest, database=weppcloud, rotation_id=41, man_path=/workdir/wepppy/wepppy/wepp/management/data/UnDisturbed/Old_Forest.man),
#  'Developed/Open Space': CropRotation(crop_name=Developed/Open Space, database=weppcloud, rotation_id=21, man_path=/workdir/wepppy/wepppy/wepp/management/data/UnDisturbed/Developed_Low_Intensity.man),
#  'Dry Beans': CropRotation(crop_name=Dry Beans, database=plant_file_db, rotation_id=beans,spr,CONV,_cm8-wepp.man, man_path=/wc1/runs/co/copacetic-note/ag_fields/plant_files/beans,spr,CONV,_cm8-wepp.man),
#  'Evergreen Forest': CropRotation(crop_name=Evergreen Forest, database=weppcloud, rotation_id=42, man_path=/workdir/wepppy/wepppy/wepp/management/data/UnDisturbed/Old_Forest.man),
#  'Fallow/Idle Cropland': CropRotation(crop_name=Fallow/Idle Cropland, database=weppcloud, rotation_id=31, man_path=/workdir/wepppy/wepppy/wepp/management/data/GeoWEPP/grass.man),
#  'Forest': CropRotation(crop_name=Forest, database=weppcloud, rotation_id=42, man_path=/workdir/wepppy/wepppy/wepp/management/data/UnDisturbed/Old_Forest.man),
#  'Grass/Pasture': CropRotation(crop_name=Grass/Pasture, database=weppcloud, rotation_id=73, man_path=/workdir/wepppy/wepppy/wepp/management/data/GIS/Poor grass.man),
#  'Herbaceous Wetlands': CropRotation(crop_name=Herbaceous Wetlands, database=weppcloud, rotation_id=73, man_path=/workdir/wepppy/wepppy/wepp/management/data/GIS/Poor grass.man),
#  'Lentils': CropRotation(crop_name=Lentils, database=plant_file_db, rotation_id=lentils,spr,NT,_cm8-wepp.man, man_path=/wc1/runs/co/copacetic-note/ag_fields/plant_files/lentils,spr,NT,_cm8-wepp.man),
#  'Millet': CropRotation(crop_name=Millet, database=weppcloud, rotation_id=73, man_path=/workdir/wepppy/wepppy/wepp/management/data/GIS/Poor grass.man),
#  'Mustard': CropRotation(crop_name=Mustard, database=weppcloud, rotation_id=73, man_path=/workdir/wepppy/wepppy/wepp/management/data/GIS/Poor grass.man),
#  'Oats': CropRotation(crop_name=Oats, database=plant_file_db, rotation_id=oats,spr,_CONV,_cm8-wepp.man, man_path=/wc1/runs/co/copacetic-note/ag_fields/plant_files/oats,spr,_CONV,_cm8-wepp.man),
#  'Other Hay/Non Alfalfa': CropRotation(crop_name=Other Hay/Non Alfalfa, database=weppcloud, rotation_id=73, man_path=/workdir/wepppy/wepppy/wepp/management/data/GIS/Poor grass.man),
#  'Peas': CropRotation(crop_name=Peas, database=plant_file_db, rotation_id=peas,spr,NT,_cm8-wepp.man, man_path=/wc1/runs/co/copacetic-note/ag_fields/plant_files/peas,spr,NT,_cm8-wepp.man),
#  'Shrubland': CropRotation(crop_name=Shrubland, database=weppcloud, rotation_id=51, man_path=/workdir/wepppy/wepppy/wepp/management/data/UnDisturbed/Shrub.man),
#  'Sod/Grass Seed': CropRotation(crop_name=Sod/Grass Seed, database=weppcloud, rotation_id=73, man_path=/workdir/wepppy/wepppy/wepp/management/data/GIS/Poor grass.man),
#  'Spring Wheat': CropRotation(crop_name=Spring Wheat, database=plant_file_db, rotation_id=wheat,spr,MT,_cm8,_fchisel-wepp.man, man_path=/wc1/runs/co/copacetic-note/ag_fields/plant_files/wheat,spr,MT,_cm8,_fchisel-wepp.man),
#  'Sunflower': CropRotation(crop_name=Sunflower, database=weppcloud, rotation_id=73, man_path=/workdir/wepppy/wepppy/wepp/management/data/GIS/Poor grass.man),
#  'Triticale': CropRotation(crop_name=Triticale, database=weppcloud, rotation_id=73, man_path=/workdir/wepppy/wepppy/wepp/management/data/GIS/Poor grass.man),
#  'Winter Wheat': CropRotation(crop_name=Winter Wheat, database=plant_file_db, rotation_id=wheat,winter,MT,_cm8-wepp.man, man_path=/wc1/runs/co/copacetic-note/ag_fields/plant_files/wheat,winter,MT,_cm8-wepp.man)}

class CropRotationManager:
    """
    Manages crop rotation for agricultural fields.

    encapsulates the logic to associate crops with management files

    user will use webform to produce a tsv file with three columns:
    - crop_name
    - database (weppcloud or plant_file_db)
    - rotation_id (weppcloud dom/nlcd id or plant file name)
    and place it in ag_fields_dir/rotation_lookup.tsv
    """
    def __init__(self, ag_fields_dir: str, landuse_mapping: str, logger_name: str | None):
        logger = logging.getLogger(logger_name or __name__)

        # get the path and verify it exists
        crop_name = _join(ag_fields_dir, 'rotation_lookup.tsv')

        if not _exists(crop_name):
            raise FileNotFoundError(f'Crop key-value lookup TSV file not found: {crop_name}')
        
        # parse the file
        rotation_lookup = {}
        with open(crop_name, 'r') as f:
            lines = f.readlines()
            if not lines:
                raise ValueError(f'Crop key-value lookup TSV file is empty: {crop_name}')
            
        for line in lines:
            if line.startswith('#') or not line.strip():
                continue
            if line.startswith('crop_name'): # skip header
                continue

            parts = re.sub(r'\t+', '\t', line.strip()).split('\t')
            if len(parts) != 3:
                raise ValueError(f'Invalid line in crop key-value lookup TSV file: {line.strip()}')
            
            crop_name = parts[0].strip()
            database = parts[1].strip()
            rotation_id = parts[2].strip().replace(' ', '_')  # normalize file names by removing spaces

            # remove quotes if present
            if (rotation_id[0] == '"' and rotation_id[-1] == '"') or \
               (rotation_id[0] == "'" and rotation_id[-1] == "'"):
                rotation_id = rotation_id[1:-1]

            rotation_lookup[crop_name] = self.resolve_rotation(
                ag_fields_dir,
                landuse_mapping,
                crop_name,
                database,
                rotation_id,
                logger_name=logger_name,
            )

        self.ag_fields_dir = ag_fields_dir
        self.rotation_lookup: Dict[str, CropRotation] = rotation_lookup
        self.logger_name = logger_name

    @staticmethod
    def resolve_rotation(
        ag_fields_dir: str,
        landuse_mapping: str,
        crop_name: str,
        database: str,
        rotation_id: str,
        *,
        logger_name: str | None,
    ) -> CropRotation:
        logger = logging.getLogger(logger_name or __name__)
        normalized_id = rotation_id.strip().replace(' ', '_')
        if database not in {'weppcloud', 'plant_file_db'}:
            raise ValueError(f'Invalid management file source: {database}')
        if database == 'plant_file_db':
            path_token = PurePosixPath(normalized_id.replace('\\', '/'))
            if path_token.is_absolute() or len(path_token.parts) != 1:
                raise ValueError('Plant management lookup must be a .man basename without path components.')
            if not normalized_id.lower().endswith('.man'):
                raise ValueError(f'Management file must be specified as lookup value: {normalized_id}')
            normalized_id = f'{Path(normalized_id).stem}.man'
            man_path = _join(ag_fields_dir, 'plant_files', normalized_id)
            if not _exists(man_path):
                raise FileNotFoundError(f'Management file not found: {man_path}')
        else:
            if not isint(normalized_id):
                raise ValueError(f'WEPP Cloud management file ID must be an integer: {normalized_id}')
            try:
                man_path = get_management_summary(normalized_id, landuse_mapping).man_path
            except InvalidManagementKey as exc:
                logger.error('Error getting management summary for %s: %s', normalized_id, exc)
                raise ValueError(f'Invalid WEPP Cloud management lookup id: {normalized_id}') from exc
        return CropRotation(
            crop_name,
            CropRotationDatabase(database),
            normalized_id,
            man_path,
        )

    def dump_rotation_lookup(self) -> None:
        # dump to tsv
        with open(_join(self.ag_fields_dir, 'rotation_lookup_dump.tsv'), 'w') as f:
            f.write('crop_name\tdatabase\trotation_id\n')
            for crop, rotation in self.rotation_lookup.items():
                f.write(f'{crop}\t{rotation.database}\t{rotation.rotation_id}\n')

    def build_rotation_stack(self, crop_rotation_schedule: List[str], man_filepath: str) -> None:
        stack = []
        for crop in crop_rotation_schedule:
            if crop not in self.rotation_lookup:
                raise ValueError(f'Crop "{crop}" not found in rotation lookup.')
            man = read_management(self.rotation_lookup[crop].man_path)
            stack.append(man)
            
        full_rotation = ManagementRotationSynth(stack, mode='stack-and-merge')
        full_rotation.write(man_filepath)
                
_thisdir = os.path.dirname(__file__)
_template_dir = _join(_thisdir, 'run_templates')


def _template_loader(fn: str) -> str:
    global _template_dir

    with open(_join(_template_dir, fn)) as fp:
        _template = fp.readlines()

        # the watershedslope.template contains comments.
        # here we strip those out
        _template = [L[:L.find('#')] for L in _template]
        _template = [L.strip() for L in _template]
        _template = '\n'.join(_template)

    return _template


def run_wepp_subfield(
    wd: str,
    field_id: int,
    topaz_id: str,
    wepp_id: int,
    sub_field_id: int,
    crop_rotation_schedule: Iterable[str],
    clip_hillslopes: bool,
    clip_hillslope_length: Optional[float],
    wepp_bin: str,
    logger_name: Optional[str] = None,
) -> None:
    
    logger = logging.getLogger(logger_name or __name__)
    rotation_schedule = list(crop_rotation_schedule)
    logger.info(
        'run_wepp_subfield(field_id=%s, topaz_id=%s, wepp_id=%s, sub_field_id=%s, crop_rotation_schedule=%s, '
        'clip_hillslopes=%s, clip_hillslope_length=%s)',
        field_id,
        topaz_id,
        wepp_id,
        sub_field_id,
        rotation_schedule,
        clip_hillslopes,
        clip_hillslope_length,
    )
    
    climate = Climate.getInstance(wd)
    landuse = Landuse.getInstance(wd)
    
    sim_years = climate.input_years

    ag_field_dir = _join(wd, 'ag_fields')
    ag_field_wepp_runs_dir = _join(wd, 'wepp/ag_fields/runs')

    # slope - copy the slope generated by peridot
    slp_path = _join(ag_field_dir, 'sub_fields/slope_files', f'field_{field_id}_{topaz_id}.slp')
    slp_relpath = f'p{sub_field_id}.slp'
    if clip_hillslopes:
        if clip_hillslope_length is None:
            raise ValueError('clip_hillslope_length must be provided when clip_hillslopes is True.')
        logger.info(f'  Clipping slope file {slp_path} to max hillslope length {clip_hillslope_length} m')
        clip_slope_file_length(slp_path, _join(ag_field_wepp_runs_dir, slp_relpath), clip_hillslope_length)
    else:
        logger.info(f'  Copying slope file {slp_path} to {slp_relpath}')
        shutil.copyfile(slp_path, _join(ag_field_wepp_runs_dir, slp_relpath))
    
    # soil - copy the soil file from the project
    soil_path = _join(wd, 'wepp/runs', f'p{wepp_id}.sol')
    sol_relpath = os.path.relpath(soil_path, ag_field_wepp_runs_dir)

    # climate - copy the climate file from the project
    climate_path = _join(wd, 'wepp/runs', f'p{wepp_id}.cli')
    cli_relpath = os.path.relpath(climate_path, ag_field_wepp_runs_dir)

    # management - create a management file for the crop rotation
    man_relpath = f'p{sub_field_id}.man'

    rotation_manager = CropRotationManager(ag_field_dir, landuse.mapping, logger_name=None)
    rotation_manager.build_rotation_stack(rotation_schedule, _join(ag_field_wepp_runs_dir, man_relpath))
    
    _wepp_run_sub_field_template = _template_loader('sub_field.template')
    run_fn = f'p{sub_field_id}.run'
    run_path = _join(ag_field_wepp_runs_dir, run_fn)
    with open(run_path, 'w') as f:
        f.write(_wepp_run_sub_field_template.format(
            sub_field_id=sub_field_id,
            man_relpath=man_relpath,
            slp_relpath=slp_relpath,
            cli_relpath=cli_relpath,
            sol_relpath=sol_relpath,
            sim_years=sim_years
        ))

    logger.info(f'  Created WEPP run file: {run_path}')
    run_hillslope(sub_field_id, 
                  ag_field_wepp_runs_dir,
                  wepp_bin=wepp_bin,
                  no_file_checks=True)
