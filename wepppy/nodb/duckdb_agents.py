from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import duckdb

__all__ = [
    'get_soil_sub_summary',
    'get_soil_subs_summary',
    'get_landuse_sub_summary',
    'get_landuse_subs_summary',
    'get_watershed_sub_summary',
    'get_watershed_subs_summary',
    'get_watershed_chn_summary',
    'get_watershed_chns_summary',
]

def _get_sub_summary(parquet_fn, topaz_id):
    with duckdb.connect() as con:
        result = con.execute(f"SELECT * FROM read_parquet('{parquet_fn}') WHERE TopazID = ?", [topaz_id]).fetchall()
        
        columns = [desc[0] for desc in con.description]
        result = [dict(zip(columns, row)) for row in result]
        return result[0]


def _get_subs_summary(parquet_fn, return_as_df):
    with duckdb.connect() as con:
        if return_as_df:
            return con.execute(f"SELECT * FROM read_parquet('{parquet_fn}')").fetchdf()
        
        result = con.execute(f"SELECT * FROM read_parquet('{parquet_fn}')").fetchall()
        
        topaz_id_index = 0
        columns = []
        
        for i, desc in enumerate(con.description):
            columns.append(desc[0])
            if desc[0] == 'TopazID':
                topaz_id_index = i

        dict_result = {row[topaz_id_index]: dict(zip(columns, row)) for row in result}
        return dict_result
    

def get_soil_sub_summary(wd, topaz_id):
    parquet_fn = _join(wd, 'soils/soils.parquet')
    return _get_sub_summary(parquet_fn, topaz_id)


def get_soil_subs_summary(wd, return_as_df=False):
    parquet_fn = _join(wd, 'soils/soils.parquet')
    return _get_subs_summary(parquet_fn, return_as_df=return_as_df)


def get_landuse_sub_summary(wd, topaz_id):
    parquet_fn = _join(wd, 'landuse/landuse.parquet')
    return _get_sub_summary(parquet_fn, topaz_id)


def get_landuse_subs_summary(wd, return_as_df=False):
    parquet_fn = _join(wd, 'landuse/landuse.parquet')
    return _get_subs_summary(parquet_fn, return_as_df=return_as_df)
        

def get_watershed_subs_summary(wd, return_as_df=False):
    parquet_fn = _join(wd, 'watershed/hillslopes.parquet')
    return _get_subs_summary(parquet_fn, return_as_df=return_as_df)

def get_watershed_sub_summary(wd, topaz_id):
    parquet_fn = _join(wd, 'watershed/hillslopes.parquet')
    return _get_sub_summary(parquet_fn, topaz_id)


def get_watershed_chn_summary(wd, topaz_id):
    parquet_fn = _join(wd, 'watershed/channels.parquet')
    return _get_sub_summary(parquet_fn, topaz_id)


def get_watershed_chns_summary(wd, return_as_df=False):
    parquet_fn = _join(wd, 'watershed/channels.parquet')
    return _get_subs_summary(parquet_fn, return_as_df=return_as_df)
