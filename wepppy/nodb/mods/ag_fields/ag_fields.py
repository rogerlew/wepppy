from __future__ import annotations
from dataclasses import dataclass
import re
from typing import List, Optional, Dict, Any, Tuple

import os
import hashlib
import time
import logging

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from os.path import isdir
from csv import DictWriter
import base64
import zipfile
import pandas as pd
from functools import partial
from copy import deepcopy

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from enum import Enum, IntEnum
from copy import deepcopy
from glob import glob
import shutil

from wepp_runner.wepp_runner import run_hillslope

from wepppy.all_your_base.all_your_base import isint
from wepppy.export.gpkg_export import gpkg_extract_objective_parameter
from wepppy.nodb.core import Watershed
from wepppy.topo.peridot.peridot_runner import run_peridot_wbt_sub_fields_abstraction, post_abstract_sub_fields
from wepppy.wepp.management.utils import ManagementRotationSynth, downgrade_to_98_4_format
from wepppy.wepp.management.managements import read_management, WEPPPY_MAN_DIR
from wepppy.wepp.management import get_management_summary, InvalidManagementKey

from wepppy.topo.watershed_abstraction.slope_file import clip_slope_file_length

from wepppy.nodb.core import *
from wepppy.nodb.base import *

__all__ = [
    'AgFieldsNoDbLockedException',
    'AgFields',
]

class AgFieldsNoDbLockedException(Exception):
    pass


class AgFields(NoDbBase):
    """
    AgFields
    """
    __name__ = 'AgFields'

    __exclude__ = ('_w3w', 
                   '_locales', 
                   '_enable_landuse_change',
                   '_dem_db',
                   '_boundary')

    filename = 'ag_fields.nodb'

    def __init__(self, wd, cfg_fn='disturbed_9002.cfg', run_group=None, group_name=None):
        super(AgFields, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

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

    @property
    def field_n(self):
        return getattr(self, '_field_n', 0)

    @property
    def sub_field_n(self):
        return getattr(self, '_sub_field_n', 0)

    @property
    def sub_field_fp_n(self):
        return getattr(self, '_sub_field_fp_n', 0)

    @property
    def geojson_timestamp(self):
        return getattr(self, '_geojson_timestamp', None)

    @property
    def geojson_is_valid(self):
        return getattr(self, '_geojson_is_valid', False)

    @property
    def field_columns(self):
        return deepcopy(getattr(self, '_field_columns', []))
    
    @property
    def field_boundaries_geojson(self):
        return self._field_boundaries_geojson

    @property
    def field_id_key(self):
        return self._field_id_key

    def validate_field_boundary_geojson(self, fn):
        geojson_path = _join(self.ag_fields_dir, fn)
        if not _exists(geojson_path):
            raise FileNotFoundError(f'Field boundary geojson file not found: {geojson_path}')

        with self.locked():
            self._field_boundaries_geojson = fn

        import geopandas as gpd
        df = gpd.read_file(geojson_path,  ignore_geometry=True)

        # make sure df has field_id column
        if 'field_id' not in df.columns:
            raise ValueError(f'field_id column not found in field boundary GeoJSON: {geojson_path}')

        # warn if field_id is not unique
        if df['field_id'].duplicated().any():
            duplicates = df[df['field_id'].duplicated()]['field_id'].tolist()
            duplicates = set(duplicates)
            self.logger.warn(f'Duplicate field_id values found in field boundary GeoJSON: {duplicates}')

        # dump attributes to parquet
        df.to_parquet(self.rotation_schedule_parquet, index=False)

        with self.locked():
            self._field_n = len(df)
            self._geojson_hash = hashlib.sha1(open(geojson_path, 'rb').read()).hexdigest()
            self._geojson_timestamp = int(time.time())
            self._geojson_is_valid = True
            self._field_columns = list([str(col) for col in df.columns])

        return dict(field_id_duplicates=duplicates)

    def get_unique_crops(self) -> set:
        # get the set of unique crops in the rotation schedule
        rotation_schedule_df = pd.read_parquet(self.rotation_schedule_parquet)
        unique_crops = set()
        for year in self._crop_year_iter():
            column_key = self.get_rotation_key(year)
            unique_crops.update(rotation_schedule_df[column_key].unique())
        return unique_crops

    def set_field_id_key(self, key: str):
        if not self.field_boundaries_geojson:
            raise ValueError("field_boundaries_geojson is not set. Call validate_field_boundary_geojson first.")

        if key not in self.field_columns:
            raise ValueError(f'field_id_key "{key}" not found in field boundary GeoJSON columns: {self.field_columns}')

        with self.locked():
            self._field_id_key = key

    @property
    def field_boundaries_tif(self):
        return _join(self.ag_fields_dir, 'field_boundaries.tif')
    
    def rasterize_field_boundaries_geojson(self):
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
        template_filepath = self.dem_fn
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

        if gdf.crs is None:
            raise ValueError(f'Field boundary GeoJSON "{geojson_path}" lacks a coordinate reference system; one is required to rasterize.')

        original_bounds = gdf.total_bounds
        has_nonzero_field_ids = bool((gdf[self.field_id_key] != 0).any())

        # Open the template DEM to get its metadata (CRS, transform, dimensions)
        with rasterio.open(template_filepath) as src:
            meta = src.meta.copy()
            template_crs = src.crs
            template_bounds = src.bounds

            if template_crs is None:
                raise ValueError(f'DEM "{template_filepath}" lacks a coordinate reference system; unable to rasterize fields.')

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
            raise ValueError(
                'Field boundary geometries do not overlap the DEM extent after reprojection. '
                'Check that the GeoJSON covers the same area as the DEM or update the CRS definition.'
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
    def sub_field_min_area_threshold_m2(self):
        return getattr(self, '_sub_field_min_area_threshold_m2', 0.0)
    
    @sub_field_min_area_threshold_m2.setter
    @nodb_setter
    def sub_field_min_area_threshold_m2(self, value: float):
        if value < 0.0:
            raise ValueError('sub_field_min_area_threshold_m2 must be non-negative.')
        self._sub_field_min_area_threshold_m2 = float(value)

    def periodot_abstract_sub_fields(
        self,
        sub_field_min_area_threshold_m2: Optional[float] = None,
        verbose: bool = True
    ):
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

    def get_sub_field_translator(self) -> Dict[str, Tuple [int, int, int] ]:
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
    def sub_fields_map(self):
        return _join(self.ag_fields_dir, 'sub_fields/sub_field_id_map.tif')

    @property
    def sub_fields_geojson(self):
        return _join(self.ag_fields_dir, 'sub_fields/sub_fields.geojson')

    @property
    def sub_fields_wgs_geojson(self):
        return _join(self.ag_fields_dir, 'sub_fields/sub_fields.WGS.geojson')

    def polygonize_sub_fields(self):
        """
        polygonize sub fields
        """
        from .polygonize_sub_fields import polygonize_sub_fields

        polygonize_sub_fields(
            self.sub_fields_map, 
            self.get_sub_field_translator(),
            self.sub_fields_geojson)

    @property
    def rotation_schedule_parquet(self):
        return _join(self.ag_fields_dir, 'rotation_schedule.parquet')

    @property
    def ag_field_wepp_runs_dir(self):
        return _join(self.wd, 'wepp/ag_fields/runs')

    @property
    def ag_field_wepp_output_dir(self):
        return _join(self.wd, 'wepp/ag_fields/output')

    @property
    def ag_fields_dir(self):
        return _join(self.wd, 'ag_fields')

    @property
    def plant_files_dir(self):
        return _join(self.ag_fields_dir, 'plant_files')

    @property
    def plant_files_2017_1_dir(self):
        return _join(self.plant_files_dir, '2017.1')

    def clear_ag_field_wepp_runs(self):
        if _exists(self.ag_field_wepp_runs_dir):
            shutil.rmtree(self.ag_field_wepp_runs_dir)
        os.makedirs(self.ag_field_wepp_runs_dir, exist_ok=True) 

    def clear_ag_field_wepp_outputs(self):
        if _exists(self.ag_field_wepp_output_dir):
            shutil.rmtree(self.ag_field_wepp_output_dir)
        os.makedirs(self.ag_field_wepp_output_dir, exist_ok=True)

    @property
    def rotation_accessor(self):
        return getattr(self, '_rotation_accessor', None)
    
    def set_rotation_accessor(self, candidate: str):
        """
        Defined by user, used to lookup the column in rotation_schedule_parquet.
        Must contain {} str.format is applied with year as the argument.
        """
        self.logger.info(f'set_rotation_accessor("{candidate}")')

        if '{}' not in candidate:
            self.logger.error("rotation_accessor must contain '{}' for year substitution.")
            raise ValueError("rotation_accessor must contain '{}' for year substitution.")

        climate = self.climate_instance
        start_year = climate.observed_start_year
        end_year = climate.observed_end_year

        for year in range(start_year, end_year + 1):
            column_key = candidate.format(str(year))

            if column_key not in self.field_columns:
                self.logger.error(f'Column key "{column_key}" not found in field boundary GeoJSON columns: {self.field_columns}')
                raise ValueError(f'Column key "{column_key}" not found in field boundary GeoJSON columns: {self.field_columns}')

        with self.locked():
            self._rotation_accessor = candidate
            self.logger.info(f'Set rotation_accessor to "{candidate}"')

    def handle_plant_file_db_upload(self, plant_db_zip_fn: str):
        """
        Unzip the plant file database zip files int self.plant_files_dir.
        
        The zip file should contain .man files
        
        - Normalizes file names by removing spaces and converting to underscores
        - Automatically downgrades 2017.1 plant files to 98.4
        """
        self.logger.info(f'handle_plant_file_db_upload("{plant_db_zip_fn}")')
        
        zip_path = _join(self.ag_fields_dir, plant_db_zip_fn)
        if not _exists(zip_path):
            raise FileNotFoundError(f'Plant file DB zip not found: {zip_path}')

        # open zip and extract .man files
        with self.timed('Extracting .man files from plant file DB zip'):
            with zipfile.ZipFile(zip_path, 'r') as z:
                for file_info in z.infolist():
                    if file_info.filename.endswith('.man'):
                        # read the first line of the file to check if it is a 2017.1 file
                        is_2017_1 = False
                        with z.open(file_info) as f:
                            first_line = f.readline().decode('utf-8').strip()
                            if '2017.1' in first_line:
                                is_2017_1 = True
                        
                        if is_2017_1:
                            z.extract(file_info, self.plant_files_2017_1_dir)
                            self.logger.info(f'  Extracted 2017.1 plant file {file_info.filename} to {self.plant_files_2017_1_dir}')
                            os.rename(
                                _join(self.plant_files_2017_1_dir, file_info.filename),
                                _join(self.plant_files_2017_1_dir, file_info.filename.replace(' ', '_'))
                            )
                            self.logger.info(f'. Renamed plant file {file_info.filename} to {file_info.filename.replace(" ", "_")}')
                        else:
                            z.extract(file_info, self.plant_files_dir)
                            self.logger.info(f'. Extracted plant file {file_info.filename} to {self.plant_files_dir}')
                            os.rename(
                                _join(self.plant_files_dir, file_info.filename),
                                _join(self.plant_files_dir, file_info.filename.replace(' ', '_'))
                            )
                            self.logger.info(f'. Renamed plant file {file_info.filename} to {file_info.filename.replace(" ", "_")}')

        with self.timed('Downgrading 2017.1 plant files to 98.4 format'):
            for man_path in glob(_join(self.plant_files_2017_1_dir, '*.man')):
                man_2017_1 = read_management(man_path)
                man_fn = _split(man_path)[-1]
                _man = downgrade_to_98_4_format(man_2017_1, _join(self.plant_files_dir, man_fn),
                                                first_year_only=True)
                self.logger.info(f'. Downgraded {man_fn} to 98.4 format')

        valid_plant_files = []
        with self.timed('Validating plant files'):
            for man_path in glob(_join(self.plant_files_dir, '*.man')):
                man_fn = _split(man_path)[-1]
                _man = read_management(man_path)
                valid_plant_files.append(man_fn)
                self.logger.info(f'  Valid plant file found: {man_fn}')

            with self.locked():
                self._valid_plant_files = valid_plant_files

        self.logger.info(f'Finished handling plant file DB upload for {plant_db_zip_fn}')

    def get_valid_plant_files(self) -> list[str]:
        return deepcopy(getattr(self, '_valid_plant_files', []))

    def get_rotation_key(self, year: int) -> str:  # to access Crop{year} column in rotation_schedule_parquet
        if self.rotation_accessor is None:
            raise ValueError('rotation_accessor is not set. Call set_rotation_accessor first.')
        return self.rotation_accessor.format(str(year))

    def _crop_year_iter(self):
        climate = self.climate_instance
        start_year = climate.observed_start_year
        end_year = climate.observed_end_year

        if start_year is None or end_year is None:
            raise ValueError('Climate must be observed')
        
        for year in range(start_year, end_year + 1):
            yield year

    def validate_rotation_lookup(self):  
        # the rotation_crop_to_man.tsv should be generated using an interface on the website.
        # backend identifies all the crops in the rotation schedule and then the user must map
        # then loads a table form with three columns:
        # LookupCrop, ManSource (weppcloud, plant_db), ManFileId (weppcloud id or plant file name)

        self.logger.info(f'validate_rotation_lookup')
        rotation_manager = CropRotationManager(self.ag_fields_dir, self.landuse_instance.mapping, logger_name=self.logger.name)
        from pprint import pprint
        pprint(rotation_manager.rotation_lookup)

    @property
    def subfields_parquet_path(self):
        return _join(self.ag_fields_dir, 'sub_fields/fields.parquet')

    @property
    def subfields_parquet(self):
        if not _exists(self.subfields_parquet_path):
            raise FileNotFoundError(f'Sub-fields parquet file not found: {self.subfields_parquet_path}')
        return pd.read_parquet(self.subfields_parquet_path)

    def run_wepp_ag_fields(self, max_workers: int | None = None):
        """
        Run WEPP for each sub-field defined in the Peridot output.

        e.g. rotation_schedule_year_key_func = lambda year: f'Crop{year}'
        """
        self.logger.info('run_wepp_ag_fields()')
        climate = self.climate_instance
        start_year = climate.observed_start_year
        end_year = climate.observed_end_year

        watershed = self.watershed_instance
        clip_hillslopes = watershed.clip_hillslopes
        clip_hillslope_length = watershed.clip_hillslope_length

        subfields_df = self.subfields_parquet
        rotation_schedule_df = pd.read_parquet(self.rotation_schedule_parquet)

        tasks = []
        for index, field in subfields_df.iterrows():
            field_id = field['field_id']
            topaz_id = str(field['topaz_id'])
            wepp_id = field['wepp_id']
            sub_field_id = field['sub_field_id']

            self.logger.info(f'. Running WEPP for field_id={field_id}, topaz_id={topaz_id}, wepp_id={wepp_id}, sub_field_id={sub_field_id}')

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
            return

        cpu_count = os.cpu_count() or 1
        if max_workers is None:
            max_workers = min(total_tasks, cpu_count)
        if max_workers < 1:
            max_workers = 1
        if max_workers > max(cpu_count, 16):
            max_workers = max(cpu_count, 16)

        self.logger.info(f'Submitting {total_tasks} sub-field WEPP runs with max_workers={max_workers}')

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {}
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
                    except Exception as exc:
                        for remaining in pending:
                            remaining.cancel()
                        self.logger.error(
                            f'  Sub-field run failed (field_id={field_id}, topaz_id={topaz_id}, sub_field_id={sub_field_id}): {exc}'
                        )
                        raise


class CropRotationDatabase(Enum):
    WEPP_CLOUD = 'weppcloud'
    PLANT_FILES_DB = 'plant_file_db'

    def __str__(self):
        return self.value

    def __getstate__(self):
        return self.value


class CropRotation:
    def __init__(self, crop_name: str, database: CropRotationDatabase, rotation_id: int | str, man_path: str):
        self.crop_name = crop_name
        self.database = database  # 'weppcloud' or 'plant_files'
        self.rotation_id = rotation_id  # dom key from the project's mapping or plant file name
        self.man_path = man_path  # path to management file

    def __repr__(self):
        return f'CropRotation(crop_name={self.crop_name}, database={self.database}, rotation_id={self.rotation_id}, man_path={self.man_path})'
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'crop_name': self.crop_name,
            'database': str(self.database),
            'value': self.rotation_id,
            'man_file_path': self.man_file_path,
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

        wd = _split(os.path.abspath(ag_fields_dir))[0]
        plant_files_dir = _join(ag_fields_dir, 'plant_files')

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
            
            crop_name = parts[0]
            database = parts[1]
            rotation_id = parts[2].replace(' ', '_')  # normalize file names by removing spaces

            # remove quotes if present
            if (rotation_id[0] == '"' and rotation_id[-1] == '"') or \
               (rotation_id[0] == "'" and rotation_id[-1] == "'"):
                rotation_id = rotation_id[1:-1]

            logger.debug(f'  Crop "{crop_name}" -> database="{database}", rotation_id="{rotation_id}"')

            if not database in ['weppcloud', 'plant_file_db']:
                raise ValueError(f'Invalid management file source in crop key-value lookup TSV file: {parts[1]}')
            
            if database == 'plant_file_db':
                if not rotation_id.endswith('.man'):
                    raise ValueError(f'Management file must be specified as lookup value: {rotation_id}')

            if database == 'weppcloud':
                if not isint(rotation_id):
                    raise ValueError(f'WEPP Cloud management file ID must be an integer: {rotation_id}')

            if database == 'weppcloud':
                try:
                    man = get_management_summary(rotation_id, landuse_mapping)
                    man_path = man.man_path
                except InvalidManagementKey as e:
                    logger.error(f'Error getting management summary for {rotation_id}: {e}')
                    raise ValueError(f'Invalid WEPP Cloud management lookup id: {rotation_id}')
            else:  # plant_file_db
                man_path = _join(plant_files_dir, rotation_id)
                if not _exists(man_path):
                    raise FileNotFoundError(f'Management file not found: {man_path}')

            rotation_lookup[crop_name] = CropRotation(crop_name, CropRotationDatabase(database), rotation_id, man_path)

        self.ag_fields_dir = ag_fields_dir
        self.rotation_lookup = rotation_lookup
        self.logger_name = logger_name

    def dump_rotation_lookup(self):
        # dump to tsv
        with open(_join(self.ag_fields_dir, 'rotation_lookup_dump.tsv'), 'w') as f:
            f.write('crop_name\tdatabase\trotation_id\n')
            for crop, rotation in self.rotation_lookup.items():
                f.write(f'{crop}\t{rotation.database}\t{rotation.rotation_id}\n')

    def build_rotation_stack(self, crop_rotation_schedule: List[str], man_filepath):
        stack = []
        for crop in crop_rotation_schedule:
            if crop not in self.rotation_lookup:
                raise ValueError(f'Crop "{crop}" not found in rotation lookup.')
            man = read_management(self.rotation_lookup[crop].man_path)
            stack.append(man)
            
        full_rotation = ManagementRotationSynth(stack)
        full_rotation.write(man_filepath)
                
_thisdir = os.path.dirname(__file__)
_template_dir = _join(_thisdir, 'run_templates')


def _template_loader(fn):
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
        wd, 
        field_id, 
        topaz_id, 
        wepp_id, 
        sub_field_id, 
        crop_rotation_schedule, 
        clip_hillslopes, 
        clip_hillslope_length,
        logger_name=None
    ):
    
    logger = logging.getLogger(logger_name or __name__)
    logger.info(f'run_wepp_subfield(field_id={field_id}, topaz_id={topaz_id}, wepp_id={wepp_id}, sub_field_id={sub_field_id}, crop_rotation_schedule={crop_rotation_schedule}, clip_hillslopes={clip_hillslopes}, clip_hillslope_length={clip_hillslope_length})')
    
    climate = Climate.getInstance(wd)
    landuse = Landuse.getInstance(wd)
    
    sim_years = climate.input_years

    ag_field_dir = _join(wd, 'ag_fields')
    ag_field_wepp_runs_dir = _join(wd, 'wepp/ag_fields/runs')

    # slope - copy the slope generated by peridot
    slp_path = _join(ag_field_dir, 'sub_fields/slope_files', f'field_{field_id}_{topaz_id}.slp')
    slp_relpath = f'p{sub_field_id}.slp'
    if clip_hillslopes:
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
    rotation_manager.build_rotation_stack(crop_rotation_schedule, _join(ag_field_wepp_runs_dir, man_relpath))
    
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
                  wepp_bin='wepp_dcc52a6',
                  no_file_checks=True)
