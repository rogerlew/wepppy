import geopandas as gpd
import pandas as pd

import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from wepppy.nodb.soils import Soils


def esri_compatible_colnames(df):
    # Create a dictionary to hold the mappings from original to new names
    rename_dict = {col: col.replace(' ', '_')
                           .replace('(', '')
                           .replace(')', '')
                           .replace('.', '') for col in df.columns}

    # Rename the columns and return the modified dataframe
    return df.rename(columns=rename_dict)


def gpkg_export(wd: str):
    wat_hill_fn = _join(wd, 'watershed/hillslopes.csv')

    # check if pre peridot
    if not _exists(wat_hill_fn):
        return None

    if wd.endswith('/'):
        runid = os.path.basename(os.path.dirname(wd))
    else:
        runid = os.path.basename(wd)

    gpkg_fn = _join(wd, f'export/arcmap/{runid}.gpkg')
    os.makedirs(os.path.dirname(gpkg_fn), exist_ok=True)

    if _exists(gpkg_fn):
        os.remove(gpkg_fn)

    hill_gdf = gpd.read_file(_join(wd, 'dem/topaz/SUBCATCHMENTS.WGS.JSON'))
    hill_gdf.set_crs("EPSG:4326", inplace=True)

    wat_hill_df = pd.read_csv(wat_hill_fn)
    wat_hill_df = esri_compatible_colnames(wat_hill_df)
    hill_gdf = hill_gdf.merge(wat_hill_df, left_on='TopazID', right_on='topaz_id', how='left')

    lc_hill_fn = _join(wd, 'landuse/landuse.parquet')
    if _exists(lc_hill_fn):
        lc_hill_df = pd.read_parquet(lc_hill_fn)
        columns_to_drop = ['man_dir', 'area', 'cancov_override', 'inrcov_override', 'rilcov_override', '_map', 'man_fn', 'pct_coverage', 'WeppID']
        columns_to_drop = [c for c in columns_to_drop if c in lc_hill_df.columns]
        lc_hill_df.drop(columns=columns_to_drop, inplace=True)
        lc_hill_df.rename(columns={'key': 'dom'}, inplace=True)
        lc_hill_df = esri_compatible_colnames(lc_hill_df)
        hill_gdf = hill_gdf.merge(lc_hill_df, on='TopazID', how='left')

    soils_hill_fn = _join(wd, 'soils/soils.parquet')
    soils_hill_df = None
    if _exists(soils_hill_fn):
        soils_hill_df = pd.read_parquet(soils_hill_fn)

    if soils_hill_df is None:
        soils_hill_df = Soils.getInstance(wd).hill_table

    if soils_hill_df is not None:
        columns_to_drop = ['soils_dir', 'area', 'color', 'build_date', 'desc', 'avke', 'bd', 'fname', 'pct_coverage', 'WeppID']
        columns_to_drop = [c for c in columns_to_drop if c in soils_hill_df.columns]
        soils_hill_df.drop(columns=columns_to_drop, inplace=True)
        hill_gdf = hill_gdf.merge(soils_hill_df, on='TopazID', how='left')

    hill_loss_fn = _join(wd, 'wepp/output/loss_pw0.hill.parquet')
    if _exists(hill_loss_fn):
        hill_df = pd.read_parquet(hill_loss_fn)
        # filter single storm
        columns_to_drop = [c for c in ('Type', 'Hillslopes', 'Length', 'Landuse', 'WeppID') if c in hill_df.columns]
        columns_to_drop.extend([c for c in hill_df.columns if 'Density' in c])
        hill_df.drop(columns=columns_to_drop, inplace=True)
        hill_df = esri_compatible_colnames(hill_df)
        hill_gdf = hill_gdf.merge(hill_df, on='TopazID', how='left')
        
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

    chn_gdf = gpd.read_file(_join(wd, 'dem/topaz/CHANNELS.WGS.JSON'))
    chn_gdf.set_crs("EPSG:4326", inplace=True)

    wat_chn_fn = _join(wd, 'watershed/channels.csv')
    wat_chn_df = pd.read_csv(wat_chn_fn)
    wat_chn_df = esri_compatible_colnames(wat_chn_df)
    columns_to_drop = ['WeppID']
    columns_to_drop = [c for c in columns_to_drop if c in wat_chn_df.columns]
    wat_chn_df.drop(columns=columns_to_drop, inplace=True)
    chn_gdf = chn_gdf.merge(wat_chn_df, left_on='TopazID', right_on='topaz_id', how='left')

    chn_loss_fn = _join(wd, 'wepp/output/loss_pw0.chn.parquet')
    if _exists(chn_loss_fn):
        chn_df = pd.read_parquet(chn_loss_fn)
        columns_to_drop = ['Channels and Impoundments', 'Length', 'Area', 'WeppID']
        columns_to_drop.extend([c for c in chn_df.columns if 'Density' in c])
        columns_to_drop = [c for c in columns_to_drop if c in chn_df.columns]
        chn_df.drop(columns=columns_to_drop, inplace=True)
        chn_df = esri_compatible_colnames(chn_df)
        chn_gdf = chn_gdf.merge(chn_df, on='TopazID', how='left')

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

if __name__ == '__main__':
    gpkg_export('/geodata/weppcloud_runs/bacterial-anorexia')

