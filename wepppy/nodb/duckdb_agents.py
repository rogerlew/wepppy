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
        # First, get the column names to determine which ID column exists
        columns_query = con.execute(f"SELECT * FROM read_parquet('{parquet_fn}') LIMIT 0").description
        column_names = [desc[0] for desc in columns_query]
        
        # Determine which topaz_id column exists
        if 'topaz_id' in column_names:
            id_column = 'topaz_id'
        elif 'TopazID' in column_names:
            id_column = 'TopazID'
        else:
            raise ValueError(f"Neither 'topaz_id' nor 'TopazID' column found in {parquet_fn}")
        
        result = con.execute(
            f"SELECT * FROM read_parquet('{parquet_fn}') WHERE {id_column} = ?", 
            [topaz_id]
        ).fetchall()
        
        columns = [desc[0] for desc in con.description]
        result = [dict(zip(columns, row)) for row in result]
        return result[0]


def _get_subs_summary(parquet_fn, return_as_df):
    with duckdb.connect() as con:
        if return_as_df:
            return con.execute(f"SELECT * FROM read_parquet('{parquet_fn}')").fetchdf()
        
        result = con.execute(f"SELECT * FROM read_parquet('{parquet_fn}')").fetchall()
        
        topaz_id_index = None
        columns = []
        
        for i, desc in enumerate(con.description):
            columns.append(desc[0])
            if desc[0] in ('topaz_id', 'TopazID'):
                topaz_id_index = i
                break

        if topaz_id_index is None:
            raise ValueError(f"Neither 'topaz_id' nor 'TopazID' column found in {parquet_fn}")

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
