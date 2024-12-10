import geopandas as gpd
import pandas as pd
import numpy as np

import json

import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from wepppy.nodb.soils import Soils

try:
    import f_esri
except ImportError:
    class FEsri:
        @staticmethod
        def has_f_esri():
            return False
    f_esri = FEsri()
    
def esri_compatible_colnames(df):
    # Create a dictionary to hold the mappings from original to new names
    rename_dict = {col: col.replace(' ', '_')
                           .replace('(', '')
                           .replace(')', '')
                           .replace('.', '') for col in df.columns}

    # Rename the columns and return the modified dataframe
    return df.rename(columns=rename_dict)


def gpkg_export(wd: str):

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
    
    wat_hill_fn = _join(wd, 'watershed/hillslopes.csv')
    if _exists(wat_hill_fn):
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
    if _exists(wat_chn_fn):
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

    if f_esri.has_f_esri():
        f_esri.gpkg_to_gdb(gpkg_fn, gpkg_fn.replace('.gpkg', '.gdb'))

from pandas.core.series import Series

def create_difference_map(scenario1_gpkg_fn, scenario2_gpkg_fn, difference_attributes, output_geojson_fn,  meta_attributes=None):
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
