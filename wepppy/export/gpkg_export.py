"""GeoPackage exports and comparison helpers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections import namedtuple
from os.path import exists as _exists
from os.path import join as _join
from typing import List, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from pandas.core.series import Series

from wepppy import f_esri
from wepppy.nodir.materialize import materialize_path_if_archive
from wepppy.nodir.parquet_sidecars import pick_existing_parquet_path
from wepppy.nodb.core import Soils


def esri_compatible_colnames(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names so downstream ESRI tools do not choke on them.

    Args:
        df: DataFrame whose columns should be sanitized.

    Returns:
        A copy of ``df`` with spaces/punctuation stripped from column names.
    """
    rename_dict = {
        col: col.replace(' ', '_').replace('(', '').replace(')', '').replace('.', '')
        for col in df.columns
    }
    return df.rename(columns=rename_dict)


ObjectiveParameter = namedtuple('ObjectiveParameter', ['topaz_id', 'wepp_id', 'value'])

def gpkg_extract_objective_parameter(gpkg_fn: str, obj_param: str) -> Tuple[List[ObjectiveParameter], float]:
    """Pull a ranked list (and total) for a single metric from a GeoPackage.

    Args:
        gpkg_fn: Path to the GeoPackage produced by :func:`gpkg_export`.
        obj_param: Column name to extract (see ERU metrics for valid options).

    Returns:
        Tuple with a descending list of :class:`ObjectiveParameter` entries and
        the domain-wide total for the metric.

    Raises:
        ValueError: If the requested metric is not supported.
    """

    if obj_param not in ['Soil_Loss_kg', 'Runoff_mm', 'Runoff_Volume_m3', 
                         'Subrunoff_mm', 'Subrunoff_Volume_m3', 
                         'Total_Phosphorus_kg']:
        
        raise ValueError(f"Invalid objective parameter: {obj_param}")
                                                         
    # Read the GeoPackage file, 'subcatchments' layer
    gdf = gpd.read_file(gpkg_fn, layer='subcatchments')

    # Filter features where the specified parameter is greater than 0
    param_features = gdf[gdf[obj_param] > 0.0]

    # Sort in descending order based on the parameter
    sorted_param = param_features.sort_values(obj_param, ascending=False)

    # Calculate the total value of the parameter
    total_param = float(sorted_param[obj_param].sum())

    # Create a list of ObjectiveParameter named tuples if there are features
    if len(sorted_param) > 0:
        result_list: List[ObjectiveParameter] = [
            ObjectiveParameter(str(row['TopazID']), str(row['WeppID']), float(row[obj_param]))
            for _, row in sorted_param.iterrows()
        ]
    else:
        result_list = []

    # Return the list and the total
    return result_list, total_param


def gpkg_export(wd: str) -> None:
    """Build a GeoPackage (and optional FileGDB mirror) for the run at ``wd``.

    The export routine stitches hillslope/channel geometry, run metadata,
    WEPP outputs, and optional management overlays into a single GeoPackage.
    When the optional ESRI tooling is available, a FileGDB copy is produced so
    ArcMap and Pro users can consume identical content without conversion.

    Args:
        wd: Working directory that contains the WEPP run artifacts.
    """
    from wepppy.nodb.core import Watershed
    watershed = Watershed.getInstance(wd)

    if wd.endswith('/'):
        runid = os.path.basename(os.path.dirname(wd))
    else:
        runid = os.path.basename(wd)

    gpkg_fn = _join(wd, f'export/arcmap/{runid}.gpkg')
    os.makedirs(os.path.dirname(gpkg_fn), exist_ok=True)

    if _exists(gpkg_fn):
        os.remove(gpkg_fn)

    gdb_fn = gpkg_fn.replace('.gpkg', '.gdb')
    if _exists(gdb_fn):
        try:
            shutil.rmtree(gdb_fn)
        except OSError:
            pass

    gdb_zip_fn = gpkg_fn.replace('.gpkg', '.gdb.zip')
    if _exists(gdb_zip_fn):
        os.remove(gdb_zip_fn)
    
    hill_source = materialize_path_if_archive(wd, watershed.subwta_shp, purpose="export")
    hill_gdf = gpd.read_file(hill_source) # the SUBCATCHMENTS.WGS.JSON file
    hill_gdf.set_crs("EPSG:4326", inplace=True)

    wat_hill_path = pick_existing_parquet_path(wd, "watershed/hillslopes.parquet")
    if wat_hill_path is not None:
        wat_hill_df = pd.read_parquet(wat_hill_path)
        wat_hill_df = esri_compatible_colnames(wat_hill_df)
        if 'TopazID' in wat_hill_df.columns:
            wat_hill_df['TopazID'] = wat_hill_df['TopazID'].astype('int64')
        else:
            wat_hill_df['TopazID'] = wat_hill_df['topaz_id'].astype('int64')
        hill_gdf['TopazID'] = hill_gdf['TopazID'].astype('int64')
        hill_gdf = hill_gdf.merge(wat_hill_df, left_on='TopazID', right_on='TopazID', how='left')
    else:  # deprecated
        wat_hill_csv = _join(wd, 'watershed/hillslopes.csv')
        if _exists(wat_hill_csv):  # even more deprecated
            wat_hill_df = pd.read_csv(wat_hill_csv)
            wat_hill_df = esri_compatible_colnames(wat_hill_df)
            wat_hill_df['TopazID'] = wat_hill_df['topaz_id'].astype('int64')
            wat_hill_df = wat_hill_df.drop(columns=['topaz_id'])
            hill_gdf['TopazID'] = hill_gdf['TopazID'].astype('int64')
            hill_gdf = hill_gdf.merge(wat_hill_df, left_on='TopazID', right_on='TopazID', how='left')

    lc_hill_path = pick_existing_parquet_path(wd, "landuse/landuse.parquet")
    if lc_hill_path is not None:
        lc_hill_df = pd.read_parquet(lc_hill_path)
        columns_to_drop = ['man_dir', 'area', 'cancov_override', 'inrcov_override', 'rilcov_override', '_map', 'man_fn', 'pct_coverage', 'WeppID']
        columns_to_drop = [c for c in columns_to_drop if c in lc_hill_df.columns]
        lc_hill_df.drop(columns=columns_to_drop, inplace=True)
        lc_hill_df.rename(columns={'key': 'dom'}, inplace=True)
        lc_hill_df = esri_compatible_colnames(lc_hill_df)
        if 'TopazID' in lc_hill_df.columns:
            lc_hill_df['TopazID'] = lc_hill_df['TopazID'].astype('int64')
        else:
            lc_hill_df['TopazID'] = lc_hill_df['topaz_id'].astype('int64')
        hill_gdf = hill_gdf.merge(lc_hill_df, left_on='TopazID', right_on='TopazID', how='left')

    soils_hill_df = None
    soils_hill_path = pick_existing_parquet_path(wd, "soils/soils.parquet")
    if soils_hill_path is not None:
        soils_hill_df = pd.read_parquet(soils_hill_path)

    if soils_hill_df is None:
        soils_hill_df = Soils.getInstance(wd).hill_table

    if soils_hill_df is not None:
        columns_to_drop = ['soils_dir', 'area', 'color', 'build_date', 'desc', 'avke', 'bd', 'fname', 'pct_coverage', 'WeppID']
        columns_to_drop = [c for c in columns_to_drop if c in soils_hill_df.columns]
        soils_hill_df.drop(columns=columns_to_drop, inplace=True)
        if 'TopazID' in soils_hill_df.columns:
            soils_hill_df['TopazID'] = soils_hill_df['TopazID'].astype('int64')
        else:
            soils_hill_df['TopazID'] = soils_hill_df['topaz_id'].astype('int64')
        hill_gdf = hill_gdf.merge(soils_hill_df, left_on='TopazID', right_on='TopazID', how='left')

    hill_loss_fn = _join(wd, 'wepp/output/interchange/loss_pw0.hill.parquet')
    if not _exists(hill_loss_fn):
        legacy_hill_loss_fn = _join(wd, 'wepp/output/loss_pw0.hill.parquet')
        if _exists(legacy_hill_loss_fn):
            hill_loss_fn = legacy_hill_loss_fn
    if _exists(hill_loss_fn):
        hill_df = pd.read_parquet(hill_loss_fn)
        # filter single storm
        columns_to_drop = [c for c in ('Type', 'Length', 'Landuse', 'WeppID') if c in hill_df.columns]
        columns_to_drop.extend([c for c in hill_df.columns if 'Density' in c])
        hill_df.drop(columns=columns_to_drop, inplace=True)
        hill_df = esri_compatible_colnames(hill_df)
        if 'TopazID' in hill_df.columns:
            hill_df['TopazID'] = hill_df['TopazID'].astype('int64')
        elif 'topaz_id' in hill_df.columns:
            hill_df['TopazID'] = pd.to_numeric(hill_df['topaz_id'], errors='coerce').astype('Int64')
        else:
            wepp_col = None
            for candidate in ('wepp_id', 'WeppID'):
                if candidate in hill_df.columns:
                    wepp_col = candidate
                    break
            if wepp_col is not None:
                translator = watershed.translator_factory()
                def _map_wepp_to_topaz(value: object) -> object:
                    try:
                        if pd.isna(value):
                            return pd.NA
                        return translator.top(wepp=int(value))
                    except Exception:
                        return pd.NA
                hill_df['TopazID'] = hill_df[wepp_col].map(_map_wepp_to_topaz).astype('Int64')
        overlap_cols = [c for c in hill_df.columns if c != 'TopazID' and c in hill_gdf.columns]
        if overlap_cols:
            hill_df = hill_df.drop(columns=overlap_cols)
        hill_gdf = hill_gdf.merge(hill_df, left_on='TopazID', right_on='TopazID', how='left')
        
    hill_gdf = esri_compatible_colnames(hill_gdf)
    columns_to_drop = ['topaz_id', 'pct_coverage', 'Hillslope_Area']
    columns_to_drop = [c for c in columns_to_drop if c in hill_gdf.columns]
    hill_gdf.drop(columns=columns_to_drop, inplace=True)

    units_d = {'length': 'm',
               'width': 'm',
               'area': 'm2',
               'elevation': 'm',
               'Runoff': 'mm',
               'Subrunoff': 'mm',
               'Baseflow': 'mm',
               'Runoff_Volume': 'm3',
               'Subrunoff_Volume': 'm3',
               'Baseflow_Volume': 'm3',
               'Soil_Loss': 'kg',
               'Sediment_Deposition': 'kg',
               'DepLoss': 'kg',
               'Sediment_Yield': 'kg',
               'Solub_React_Phosphorus': 'kg',
               'Particulate_Phosphorus': 'kg',
               'Total_Phosphorus': 'kg',
               }
    
    units_d = {k: f'{k}_{v}' for k, v in units_d.items()}
    hill_gdf.rename(columns=units_d, inplace=True)

    hill_gdf = esri_compatible_colnames(hill_gdf)
#    hill_gdf.to_file(_join(wd, 'export/subcatchments.geojson'), driver='GeoJSON')
    hill_gdf.to_file(gpkg_fn, driver='GPKG', layer='subcatchments')

    chn_source = materialize_path_if_archive(wd, watershed.channels_shp, purpose="export")
    chn_gdf = gpd.read_file(chn_source)  # the CHANNELS.WGS.JSON file
    chn_gdf.set_crs("EPSG:4326", inplace=True)

    wat_chn_path = pick_existing_parquet_path(wd, "watershed/channels.parquet")
    if wat_chn_path is not None:
        wat_chn_df = pd.read_parquet(wat_chn_path)
        wat_chn_df = esri_compatible_colnames(wat_chn_df)
        columns_to_drop = ['WeppID', 'order']
        columns_to_drop = [c for c in columns_to_drop if c in wat_chn_df.columns]
        wat_chn_df.drop(columns=columns_to_drop, inplace=True)
        if 'TopazID' in wat_chn_df.columns:
            wat_chn_df['TopazID'] = wat_chn_df['TopazID'].astype('int64')
        else:
            wat_chn_df['TopazID'] = wat_chn_df['topaz_id'].astype('int64')
        chn_gdf['TopazID'] = chn_gdf['TopazID'].astype('int64')
        chn_gdf = chn_gdf.merge(wat_chn_df, left_on='TopazID', right_on='TopazID', how='left')
    else:  # deprecated
        wat_chn_csv = _join(wd, 'watershed/channels.csv')
        if _exists(wat_chn_csv):  # even more deprecated
            wat_chn_df = pd.read_csv(wat_chn_csv)
            wat_chn_df = esri_compatible_colnames(wat_chn_df)
            columns_to_drop = ['WeppID']
            columns_to_drop = [c for c in columns_to_drop if c in wat_chn_df.columns]
            wat_chn_df.drop(columns=columns_to_drop, inplace=True)
            if 'TopazID' in wat_chn_df.columns:
                wat_chn_df['TopazID'] = wat_chn_df['TopazID'].astype('int64')
            else:
                wat_chn_df['TopazID'] = wat_chn_df['topaz_id'].astype('int64')
            wat_chn_df = wat_chn_df.drop(columns=['topaz_id'])
            chn_gdf['TopazID'] = chn_gdf['TopazID'].astype('int64')
            chn_gdf = chn_gdf.merge(wat_chn_df, left_on='TopazID', right_on='TopazID', how='left')

    chn_loss_fn = _join(wd, 'wepp/output/interchange/loss_pw0.chn.parquet')
    if not _exists(chn_loss_fn):
        legacy_chn_loss_fn = _join(wd, 'wepp/output/loss_pw0.chn.parquet')
        if _exists(legacy_chn_loss_fn):
            chn_loss_fn = legacy_chn_loss_fn
    if _exists(chn_loss_fn):
        chn_df = pd.read_parquet(chn_loss_fn)
        columns_to_drop = ['Length', 'Area', 'WeppID']
        columns_to_drop.extend([c for c in chn_df.columns if 'Density' in c])
        columns_to_drop = [c for c in columns_to_drop if c in chn_df.columns]
        chn_df.drop(columns=columns_to_drop, inplace=True)
        chn_df = esri_compatible_colnames(chn_df)
        if 'TopazID' in chn_df.columns:
            chn_df['TopazID'] = chn_df['TopazID'].astype('int64')
        elif 'topaz_id' in chn_df.columns:
            chn_df['TopazID'] = pd.to_numeric(chn_df['topaz_id'], errors='coerce').astype('Int64')
        elif 'chn_enum' in chn_df.columns:
            translator = watershed.translator_factory()
            def _map_chn_to_topaz(value: object) -> object:
                try:
                    if pd.isna(value):
                        return pd.NA
                    return translator.top(chn_enum=int(value))
                except Exception:
                    return pd.NA
            chn_df['TopazID'] = chn_df['chn_enum'].map(_map_chn_to_topaz).astype('Int64')
        overlap_cols = [c for c in chn_df.columns if c != 'TopazID' and c in chn_gdf.columns]
        if overlap_cols:
            chn_df = chn_df.drop(columns=overlap_cols)
        chn_gdf = chn_gdf.merge(chn_df, left_on='TopazID', right_on='TopazID', how='left')

    chn_gdf = esri_compatible_colnames(chn_gdf)
    columns_to_drop = ['Type']
    columns_to_drop = [c for c in columns_to_drop if c in chn_gdf.columns]
    chn_gdf.drop(columns=columns_to_drop, inplace=True)
    
    units_d = {'length': 'm',
               'width': 'm',
               'area': 'm2',
               'elevation': 'm',
               'Discharge_Volume': 'm3',
               'Sediment_Yield': 'tonne',
               'Soil_Loss': 'kg',
               'Upland_Charge': 'm3',
               'Subsurface_Flow_Volume': 'm3',
               'Contributing_Area': 'ha',
               'Solub_React_Phosphorus': 'kg',
               'Particulate_Phosphorus': 'kg',
               'Total_Phosphorus': 'kg',
               }
    
    units_d = {k: f'{k}_{v}' for k, v in units_d.items()}
    chn_gdf.rename(columns=units_d, inplace=True)

    chn_gdf.to_file(gpkg_fn, driver='GPKG', layer='channels')

    if f_esri.has_f_esri():
        if _exists(gdb_fn):
            _chown_and_rmtree(gdb_fn)
        f_esri.c2c_gpkg_to_gdb(gpkg_fn, gdb_fn)
        
def _chown(dir_path: str) -> None:
    """Recursively chown a directory so ArcGIS tooling can clean it up.

    Args:
        dir_path: Directory that should be re-owned by the web group user.
    """
    assert os.path.isdir(dir_path), f"{dir_path} is not a directory"

    subprocess.run(
        ["sudo", "/bin/chown", "-R", "www-data:webgroup", dir_path],
        check=True,
    )

def _chown_and_rmtree(dir_path: str) -> None:
    """Chown then remove a directory tree (used for stale GDB cleanup).

    Args:
        dir_path: Directory slated for deletion.
    """
    assert os.path.isdir(dir_path), f"{dir_path} is not a directory"
    _chown(dir_path)
    shutil.rmtree(dir_path)


def create_difference_map(
    scenario1_gpkg_fn: str,
    scenario2_gpkg_fn: str,
    difference_attributes: list[str],
    output_geojson_fn: str,
    meta_attributes: list[str] | None = None,
) -> None:
    """Generate a GeoJSON file highlighting metric deltas between scenarios.

    Args:
        scenario1_gpkg_fn: Baseline GeoPackage path for the comparison.
        scenario2_gpkg_fn: Comparison GeoPackage path with the same schema.
        difference_attributes: Metric names to compare (must exist in both).
        output_geojson_fn: Destination path that receives the GeoJSON diff.
        meta_attributes: Optional metadata keys carried over verbatim.

    Raises:
        AssertionError: If the GeoPackages disagree on CRS or feature count.
    """
    layer_name = "subcatchments"
    scenario1_gdf = gpd.read_file(scenario1_gpkg_fn, layer=layer_name)
    scenario2_gdf = gpd.read_file(scenario2_gpkg_fn, layer=layer_name)

    assert len(scenario1_gdf) == len(scenario2_gdf), "The two maps must have the same number of features."
    assert scenario1_gdf.crs == scenario2_gdf.crs, "The two maps must have the same CRS."

    features = []

    for feature1, feature2 in zip(scenario1_gdf.iterfeatures(), scenario2_gdf.iterfeatures()):
        feature1_props = feature1['properties']
        feature2_props = feature2['properties']
        
        print(feature1_props)
        
        topaz_id = feature1_props['TopazID']
        

        new_feature = {
            "type": "Feature",
            "geometry": feature1['geometry'],
            "properties": {}
        }
        
        new_feature["properties"]["topaz_id"] = topaz_id
        
        if meta_attributes is not None:
            for attr in meta_attributes:
                new_feature["properties"][attr] = feature1_props.get(attr)

        for attr in difference_attributes:
            value1 = feature1_props.get(attr, np.nan)
            value2 = feature2_props.get(attr, np.nan)
            
            difference = np.nan if np.isnan(value1) or np.isnan(value2) else value1 - value2
            new_feature["properties"][f"difference_{attr}"] = difference

        features.append(new_feature)

    geojson_output = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_geojson_fn, 'w') as f:
        json.dump(geojson_output, f, indent=2)


if __name__ == '__main__':
#    gpkg_export('/geodata/weppcloud_runs/six-serine/')

    # Carmen's burned and modified scenarios
    if 0:
        create_difference_map('/geodata/weppcloud_runs/six-serine/export/arcmap/six-serine.gpkg', 
                            '/geodata/weppcloud_runs/hedonic-disqualification/export/arcmap/hedonic-disqualification.gpkg', 
                            difference_attributes=['Soil_Loss_kg', 'Runoff_mm'],
                            output_geojson_fn='test/difference_map.geojson')
    
    
    create_difference_map('/geodata/weppcloud_runs/worldwide-trombone/export/arcmap/worldwide-trombone.gpkg', 
                          '/geodata/weppcloud_runs/multiple-principal/export/arcmap/multiple-principal.gpkg', 
                          difference_attributes=['Soil_Loss_kg', 'Runoff_mm'],
                          meta_attributes=['disturbed_class', 'simple_texture'],
                          output_geojson_fn='/geodata/weppcloud_runs/multiple-principal/export/arcmap/pinegulch_post_difference_map.geojson')

    create_difference_map('/geodata/weppcloud_runs/rlew-dependable-linchpin/export/arcmap/rlew-dependable-linchpin.gpkg', 
                          '/geodata/weppcloud_runs/rlew-miserable-morphology/export/arcmap/rlew-miserable-morphology.gpkg', 
                          difference_attributes=['Soil_Loss_kg', 'Runoff_mm'],
                          meta_attributes=['disturbed_class', 'simple_texture'],
                          output_geojson_fn='/geodata/weppcloud_runs/rlew-miserable-morphology/export/arcmap/rlew_pinegulch_post_difference_map.geojson')
