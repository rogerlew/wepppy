#!/usr/bin/env python3
"""Explicit bounded acquisition into a NEW study folder, never live Soils."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import requests
import rasterio
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import from_bounds, Window

SITES = ['moscow_mountain', 'topanga', 'az_ponderosa']
SDA = 'https://SDMDataAccess.nrcs.usda.gov/Tabular/post.rest'
ITEM = 'https://www.sciencebase.gov/catalog/item/675721b9d34e5c5dfd05c575?format=json'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--terrain',required=True,type=Path)
    parser.add_argument('--spatial-source',required=True,type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    response=requests.get(ITEM,timeout=30);response.raise_for_status()
    metadata=response.json()
    (args.output/'statsgo_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    cog=next(f['publishedS3Uri'] for f in metadata['files'] if f['name']=='STATSGO-THICK.tif')
    expected='https://prod-is-usgs-sb-prod-publish.s3.amazonaws.com/675721b9d34e5c5dfd05c575/STATSGO-THICK.tif'
    if cog!=expected:raise ValueError('USGS asset changed; review new source before acquisition')
    queries=[]
    for site in SITES:
        with rasterio.open(args.terrain/site/'10m/dem/dem.tif') as ref, rasterio.open(args.spatial_source) as src:
            profile=ref.profile.copy();profile.update(dtype='int32',nodata=0,compress='deflate')
            data=np.zeros(ref.shape,dtype='int32')
            reproject(rasterio.band(src,1),data,src_nodata=src.nodata,dst_transform=ref.transform,
                      dst_crs=ref.crs,dst_nodata=0,resampling=Resampling.nearest)
            with rasterio.open(args.output/f'{site}_mukey.tif','w',**profile) as dst:dst.write(data,1)
            keys=np.unique(data);keys=keys[keys>0]
            if not len(keys) or len(keys)>1000:raise ValueError('Empty or unexpectedly large source subset')
            key_sql=','.join(map(str,keys))
            query_defs=[
                ('lineage', 'SELECT mu.mukey,l.areasymbol,l.areatypename,sac.saversion,sac.saverest FROM mapunit mu INNER JOIN legend l ON mu.lkey=l.lkey INNER JOIN sacatalog sac ON sac.areasymbol=l.areasymbol WHERE mu.mukey IN ('+key_sql+')'),
                ('component','SELECT mukey,cokey,compname,comppct_r,compkind FROM component WHERE mukey IN ('+key_sql+') ORDER BY mukey,cokey'),
                ('chorizon','SELECT h.cokey,h.chkey,h.hzname,h.hzdept_r,h.hzdepb_r,h.hzthk_r,h.desgnmaster FROM chorizon h INNER JOIN component c ON c.cokey=h.cokey WHERE c.mukey IN ('+key_sql+') ORDER BY h.cokey,h.hzdept_r,h.chkey')]
            for table,query in query_defs:
                # Same SDA endpoint/payload contract as ssurgo.py acquisition;
                # minimal public study columns, no live collection/cache instance.
                response=requests.post(SDA,data={'query':query,'format':'JSON+COLUMNNAME'},timeout=60)
                response.raise_for_status();payload=response.json();records=payload['Table']
                if table=='lineage':
                    (args.output/f'{site}_lineage.json').write_text(json.dumps(payload)+'\n')
                    observed={int(r[0]) for r in records[1:]}
                    if observed!=set(keys):raise ValueError('Unresolved spatial MUKEY lineage')
                    if any(r[2]!='Non-MLRA Soil Survey Area' for r in records[1:]):
                        raise ValueError('Panel source lineage requires review')
                else:
                    with (args.output/f'{site}_{table}.csv').open('w',newline='') as stream:
                        csv.writer(stream).writerows(records)
                queries.append(dict(site=site,table=table,query=query,source_url=SDA,
                    format='JSON+COLUMNNAME',retrieved_utc=datetime.now(timezone.utc).isoformat(),rows=len(records)-1))
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_TIMEOUT='30'):
                with rasterio.open(cog) as reference:
                    window=from_bounds(*transform_bounds(ref.crs,reference.crs,*ref.bounds),reference.transform)
                    window=Window(math.floor(window.col_off)-2,math.floor(window.row_off)-2,
                                  math.ceil(window.width)+5,math.ceil(window.height)+5)
                    if window.width*window.height>2_000_000:raise ValueError('Unexpected COG window size')
                    values=reference.read(1,window=window)
                    output_profile=dict(reference.profile,height=values.shape[0],width=values.shape[1],
                                        transform=reference.window_transform(window),compress='deflate')
                    with rasterio.open(args.output/f'{site}_statsgo_native.tif','w',**output_profile) as dst:
                        dst.write(values,1)
    (args.output/'queries.json').write_text(json.dumps(queries,indent=2)+'\n')
    files=[]
    for path in sorted(args.output.iterdir()):
        with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        files.append(dict(path=path.name,sha256=digest,bytes=path.stat().st_size))
    (args.output/'manifest.json').write_text(json.dumps(dict(files=files,spatial_source=str(args.spatial_source),
        spatial_vintage='2025 mosaic; SDA tables retrieved separately',original_keys=True,substitutions=[],
        attribution='USDA NRCS Soil Survey; USGS Schwarz and Alexander 1995, King 2025',
        units={'horizons':'cm','STATSGO_THICK':'inches'}),indent=2)+'\n')


if __name__=='__main__':main()
