"""Fresh disposable development basin; no network or source-project writes.

Compatibility/regression plan: fork only the specified small validation template
with the canonical helper, replace fixture inputs only in the new destination,
prepare/activate through authoritative APIs, then exercise real browser/RQ.
No existing user basin or upstream cache is repaired or rebuilt.
"""
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.core import Ron, Watershed, Soils, Landuse
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.rq.project_rq_fork import prepare_fork_run
from wepppy.nodb.mods.postfire_debris_flow import rainfall_io as io
from wepppy.nodb.mods.postfire_debris_flow.source_preparation import prepare_local_sources
from wepppy.nodb.mods.postfire_debris_flow.production_soils import activate_sources
from tests.nodb.mods.test_postfire_debris_flow_production_soils import database


def main():
    source, target = (Path(p).absolute() for p in sys.argv[1:])
    assert source.name.startswith('pfdf-smoke-') and target.name.startswith('pfdf-m3-validation-')
    assert not target.exists() and target.parent == Path('/wc1/runs/pf')
    assert sum(p.stat().st_size for p in source.rglob('*') if p.is_file()) < 64*1024*1024
    prepare_fork_run(source.name,target.name,undisturbify=False,
        status_channel=target.name+':fork',publish_status=lambda *_:None,
        get_wd=lambda _:str(source),get_primary_wd=lambda _:str(target),
        wait_for_paths=lambda *_args,**_kwargs:None,ron_cls=Ron,disturbed_cls=Disturbed,
        landuse_cls=Landuse,soils_cls=Soils,initialize_ttl=None)
    history=target/'template_history';history.mkdir()
    for name in ('postfire_debris_flow','postfire_debris_flow.nodb'):
        if (target/name).exists():shutil.move(target/name,history/name)
    (target/'postfire_debris_flow').mkdir()
    ron=Ron.getInstance(str(target))
    with ron.locked():
        ron._cellsize=10;ron._dem_db='ned13/2022';ron._name='Synthetic M3 acceptance only'
    watershed=Watershed.getInstance(str(target))
    dem=Path(ron.dem_fn);mask=Path(watershed.wbt_wd)/'bound.tif';pointer=Path(watershed.wbt_wd)/'flovec.tif'
    grid=from_origin(510000,4010000,10,10)
    profile=dict(driver='GTiff',height=7,width=7,count=1,dtype='float64',crs='EPSG:32611',transform=grid,nodata=-9999)
    def write(path,values):
        with rasterio.open(path,'w',**profile) as ds: ds.write(values,1)
    elevation=np.zeros((7,7));elevation[3,2:5]=[130,90,100]
    directions=np.zeros((7,7));directions[3,2:4]=2
    domain=np.zeros((7,7));domain[3,2:5]=1
    severity=np.zeros((7,7));severity[3,2:5]=[2,3,0]
    for path,values in ((dem,elevation),(pointer,directions),(mask,domain),
        (Path(Disturbed.getInstance(str(target)).sbs_4class_path),severity),
        (target/'soils/ssurgo.tif',np.full((7,7),7.))): write(path,values)
    (Path(watershed.wbt_wd)/'outlet.geojson').write_text(json.dumps({'type':'Point','coordinates':[510045,4009965]}))
    cache=target/'soils/ssurgo_tabular_cache.sqlite'
    assert not cache.exists();database(cache)
    catalog=target/'postfire_debris_flow/validation_lineage.json'
    io.write_json(catalog,dict(schema_version=1,collection_by_mukey={'7':'SSURGO'},source='synthetic validation only',retrieved_at='2026-09-14'))
    pd.DataFrame({'prcp':[10.]*30,'year':list(range(1,31)),'month':[1]*30,'day_of_month':[1]*30,
        'peak_intensity_15':[40.]*30,'peak_intensity_30':[20.]*30,'peak_intensity_60':[10.]*30}).to_parquet(target/'climate/wepp_cli.parquet')
    receipt=prepare_local_sources(target,dem,mask,collection_catalog=catalog)
    result=activate_sources(target,receipt,expected_sha256=io.digest(receipt))
    report=dict(project=str(target),source_kind='controlled synthetic validation only',receipt=str(receipt),activation=result)
    io.write_json(target/'postfire_debris_flow/validation_fixture.json',report)
    print(json.dumps(report))


if __name__=='__main__': main()
