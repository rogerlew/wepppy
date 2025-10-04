from __future__ import annotations
from typing import List, Optional, Dict, Any

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

import pandas as pd

from functools import partial

from enum import IntEnum
from copy import deepcopy
from glob import glob
import json
import shutil
from time import sleep

# non-standard
import utm

# wepppy
from wepppy.export.gpkg_export import gpkg_extract_objective_parameter
from wepppy.nodb.watershed import Watershed

from ...base import (
    NoDbBase,
    TriggerEvents,
    nodb_setter,
    clear_locks,
    clear_nodb_file_cache,
)


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

    @property
    def field_boundaries_geojson(self):
        return self._field_boundaries_geojson

    @property
    def field_id_key(self):
        return self._field_id_key

    def validate_field_boundary_geojson(self, fn, field_id_key):
        geojson_path = _join(self.ag_fields_dir, fn)
        if not _exists(geojson_path):
            raise FileNotFoundError(f'Field boundary geojson file not found: {geojson_path}')

        with self.locked():
            self._field_boundaries_geojson = fn
            self._field_id_key = field_id_key

        import geopandas as gpd
        df = gpd.read_file(geojson_path,  ignore_geometry=True)

        if field_id_key not in df.columns:
            raise ValueError(f'Field ID key "{field_id_key}" not found in geojson properties: {df.columns.tolist()}')

        # validate the field_id_key column is numeric
        if not pd.api.types.is_numeric_dtype(df[field_id_key]):
            raise ValueError(f'Field ID key "{field_id_key}" must be numeric. Found dtype: {df[field_id_key].dtype}')
        
        df.to_parquet(self.rotation_schedule_parquet, index=False)

    @property
    def field_boundaries_tif(self):
        return _join(self.ag_fields_dir, 'field_boundaries.tif')
    
    def rasterize_field_boundaries_geojson(self):
        """
        Rasterizes the field boundaries GeoJSON file to a TIFF using the project's DEM as a template.
        The values in the raster correspond to the field IDs specified by self.field_id_key.
        """
        # ogr2ogr -f GeoJSON -t_srs EPSG:4325 field_boundaries.geojson CSB_2008_2024_Hangman_with_Crop_and_Performance.shp

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

        self.logger.info(f"Successfully created rasterized field boundaries at {output_filepath}")

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
