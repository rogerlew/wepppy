import geopandas as gpd
import pandas as pd

import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists


def gpkg_export(wd: str):
    wat_hill_fn = _join(wd, 'watershed/hillslopes.csv')

    # check if pre peridot
    if not _exists(wat_hill_fn):
        return None


    if wd.endswith('/'):
        runid = os.path.dirname(os.path.basename(wd))
    else:
        runid = os.path.basename(wd)

    gpkg_fn = _join(wd, f'export/arcmap/{runid}.gpkg')
    os.makedirs(os.path.dirname(gpkg_fn), exist_ok=True)

    if _exists(gpkg_fn):
        os.remove(gpkg_fn)

    hill_gdf = gpd.read_file(_join(wd, 'dem/topaz/SUBCATCHMENTS.WGS.JSON'))

    wat_hill_df = pd.read_csv(wat_hill_fn)
    hill_gdf = hill_gdf.merge(wat_hill_df, left_on='TopazID', right_on='topaz_id', how='left')

    lc_hill_fn = _join(wd, 'landuse/landuse.parquet')
    if _exists(lc_hill_fn):
        lc_hill_df = pd.read_parquet(lc_hill_fn)
        columns_to_drop = ['man_dir', 'area', 'cancov_override', 'inrcov_override', 'rilcov_override']
        lc_hill_df.drop(columns=columns_to_drop, inplace=True)
        lc_hill_df.rename(columns={'key': 'dom'}, inplace=True)
        hill_gdf = hill_gdf.merge(lc_hill_df, on='TopazID', how='left')

    soils_hill_fn = _join(wd, 'soils/soils.parquet')
    if _exists(soils_hill_fn):
        soils_hill_df = pd.read_parquet(soils_hill_fn)
        columns_to_drop = ['soils_dir', 'area', 'color', 'build_date', 'desc',  'pct_coverage', 'avke', 'bd']
        soils_hill_df.drop(columns=columns_to_drop, inplace=True)
        hill_gdf = hill_gdf.merge(soils_hill_df, on='TopazID', how='left')

    hill_loss_fn = _join(wd, 'wepp/output/loss_pw0.hill.parquet')
    if _exists(hill_loss_fn):
        hill_df = pd.read_parquet(hill_loss_fn)
        columns_to_drop = ['Type', 'Hillslopes', 'Length', 'Landuse']
        hill_df.drop(columns=columns_to_drop, inplace=True)
        hill_gdf = hill_gdf.merge(hill_df, on='TopazID', how='left')

    hill_gdf.to_file(gpkg_fn, driver='GPKG', layer='subcatchments')

    chn_gdf = gpd.read_file(_join(wd, 'dem/topaz/CHANNELS.WGS.JSON'))

    wat_chn_fn = _join(wd, 'watershed/channels.csv')
    wat_chn_df = pd.read_csv(wat_chn_fn)
    chn_gdf = chn_gdf.merge(wat_chn_df, left_on='TopazID', right_on='topaz_id', how='left')

    chn_loss_fn = _join(wd, 'wepp/output/loss_pw0.chn.parquet')
    if _exists(chn_loss_fn):
        chn_df = pd.read_parquet(chn_loss_fn)
        columns_to_drop = ['Channels and Impoundments', 'Length', 'Area']
        chn_df.drop(columns=columns_to_drop, inplace=True)
        chn_gdf = chn_gdf.merge(chn_df, on='TopazID', how='left')

    chn_gdf.to_file(gpkg_fn, driver='GPKG', layer='channels')

if __name__ == '__main__':
    gpkg_export('/geodata/weppcloud_runs/rlew-extragalactic-beechnut')

