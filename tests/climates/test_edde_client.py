"""Native-grid, real NetCDF extraction, and bounded transport contracts."""
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd
import pytest

from wepppy.climates.edde.client import (
    AvailabilityError, DataQualityError, EddeClient, EligibilityError, Point, locate,
)

pytestmark = pytest.mark.unit


def test_public_requests_ignore_ambient_credentials(tmp_path, monkeypatch):
    import requests
    credentials = tmp_path / 'netrc'
    credentials.write_text('machine epa-edde-v2.s3.amazonaws.com login synthetic password synthetic\n')
    monkeypatch.setenv('NETRC', str(credentials))
    client = EddeClient(tmp_path / 'cache')
    request = client.session.prepare_request(requests.Request('GET', 'https://epa-edde-v2.s3.amazonaws.com/'))
    assert 'Authorization' not in request.headers


def make_grid(path):
    with netCDF4.Dataset(path, 'w', format='NETCDF3_CLASSIC') as ds:
        ds.createDimension('x', 2)
        ds.createDimension('y', 2)
        ds.CRS = '+proj=eqc +lat_ts=0 +lon_0=0 +datum=WGS84 +units=m'
        ds.createVariable('x', 'f8', ('x',))[:] = [0, 12000]
        ds.createVariable('y', 'f8', ('y',))[:] = [0, 12000]
        ds.createVariable('lon', 'f4', ('y','x'))[:] = [[0,.1078],[0,.1078]]
        ds.createVariable('lat', 'f4', ('y','x'))[:] = [[0,0],[.1078,.1078]]
        ds.createVariable('LANDMASK', 'i4', ('y','x'))[:] = [[1,0],[1,1]]


def make_data(path, *, missing=False, gap=False):
    make_grid(path)
    with netCDF4.Dataset(path, 'a') as ds:
        ds.createDimension('time', None)
        t = ds.createVariable('time', 'f8', ('time',))
        t.units = 'hours since 2000-01-01'
        t.calendar = 'standard'
        t[:] = [0,48] if gap else [0,24]
        v = ds.createVariable('PRECIP','f4',('time','y','x'),fill_value=-1e20)
        v.units = 'kg m-2'
        v[:] = [[[1,2],[3,4]],[[5,6],[7,8]]]
        if missing:
            v[1,0,0] = -1e20


def client_fixture(tmp_path, monkeypatch, **kwargs):
    grid, data = tmp_path/'grid.nc', tmp_path/'data.nc'
    make_grid(grid)
    make_data(data, **kwargs)
    obj = dict(key='EDDE_V2/daily/WRF-MPI/Historical/2000/prday.test.2000-01.raw.nc',
               size=data.stat().st_size,etag='"fixture"')
    client = EddeClient(tmp_path/'cache')
    monkeypatch.setattr(client,'inventory',lambda *args:[obj])
    monkeypatch.setattr(client,'grid',lambda *args:(grid,{}))
    monkeypatch.setattr(client,'fetch',lambda value:(data,{'source':value}))
    return client


def test_cell_face_domain_and_landmask(tmp_path):
    grid=tmp_path/'grid.nc'
    make_grid(grid)
    assert locate(grid,[Point('inside',0,0)])[0]['row']==0
    with pytest.raises(EligibilityError,match='outside'):
        locate(grid,[Point('outside',-1,0)])
    with pytest.raises(EligibilityError,match='land'):
        locate(grid,[Point('ocean',.1078,0)])
    # Bounds extend half a cell beyond the centers; no lat/lon bbox shortcut.
    assert locate(grid,[Point('edge',-.04,0)])[0]['col']==0


def test_extract_actual_netcdf_values_at_multiple_cells(tmp_path,monkeypatch):
    client=client_fixture(tmp_path,monkeypatch)
    table,meta=client.query([Point('a',0,0),Point('b',.1078,.1078)],
                            'WRF-MPI','Historical','2000-01-01','2000-01-02',['prday'])
    assert table[table.point=='a'].prday.tolist()==[1,5]
    assert table[table.point=='b'].prday.tolist()==[4,8]
    assert meta['objects'][0]['units']=='kg m-2'
    assert meta['status']=='complete'


@pytest.mark.parametrize('kwargs,match', [({'missing':True},'Missing/nonfinite'),
                                         ({'gap':True},'Incomplete or duplicate')])
def test_reject_source_defects(tmp_path,monkeypatch,kwargs,match):
    client=client_fixture(tmp_path,monkeypatch,**kwargs)
    with pytest.raises(DataQualityError,match=match):
        client.query([Point('a',0,0)],'WRF-MPI','Historical','2000-01-01','2000-01-02',['prday'])


def test_missing_variable_and_short_date_coverage(tmp_path,monkeypatch):
    client=client_fixture(tmp_path,monkeypatch)
    with pytest.raises(AvailabilityError):
        client.query([Point('a',0,0)],'WRF-MPI','Historical','2000-01-01','2000-01-02',['unknown'])
    with pytest.raises(DataQualityError,match='Incomplete requested'):
        client.query([Point('a',0,0)],'WRF-MPI','Historical','2000-01-01','2000-01-03',['prday'])


@pytest.mark.parametrize('name,lon,lat',[('../bad',0,0),('x',float('nan'),0),('x',181,0),('x',0,91)])
def test_invalid_point(name,lon,lat):
    with pytest.raises(ValueError): Point(name,lon,lat)


class Response:
    def __init__(self, payload, etag='"one"'):
        self.payload=payload
        self.headers={'ETag':etag}
        self.status_code=200
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def raise_for_status(self): pass
    def iter_content(self,size): yield self.payload


def test_cache_integrity_and_partial_failure(tmp_path,monkeypatch):
    client=EddeClient(tmp_path,max_download_bytes=10)
    obj=dict(key='EDDE_V2/test.nc',size=4,etag='"one"')
    calls=[]
    def get(*args,**kwargs):
        calls.append(kwargs)
        return Response(b'good')
    monkeypatch.setattr(client.session,'get',get)
    path,first=client.fetch(obj)
    assert first['cache_hit'] is False
    _,second=client.fetch(obj)
    assert second['cache_hit'] is True and len(calls)==1
    path.write_bytes(b'evil')
    _,third=client.fetch(obj)
    assert third['cache_hit'] is False and path.read_bytes()==b'good'
    assert calls[0]['headers']=={'If-Match':'"one"'}
    with pytest.raises(ValueError,match='budget'):
        client.fetch(dict(key='EDDE_V2/large.nc',size=20,etag='"one"'))
    client.downloaded_bytes=0
    monkeypatch.setattr(client.session,'get',lambda *a,**k:Response(b'x'))
    with pytest.raises(DataQualityError,match='Truncated'):
        client.fetch(dict(key='EDDE_V2/short.nc',size=4,etag='"one"'))
    assert len(list(tmp_path.glob('*.partial')))==1
    assert len(list(tmp_path.glob('*.nc')))==1


def test_changed_object_and_unsafe_key(tmp_path,monkeypatch):
    client=EddeClient(tmp_path)
    monkeypatch.setattr(client.session,'get',lambda *a,**k:Response(b'good','"different"'))
    with pytest.raises(DataQualityError,match='identity'):
        client.fetch(dict(key='EDDE_V2/test.nc',size=4,etag='"one"'))
    with pytest.raises(ValueError,match='Unsafe'):
        client.fetch(dict(key='EDDE_V2/../escape.nc',size=4,etag='"one"'))


def test_pagination_and_failed_continuation(tmp_path,monkeypatch):
    client=EddeClient(tmp_path)
    calls=[]
    def get(*args,**kwargs):
        calls.append(dict(kwargs['params']))
        truncated=len(calls)==1
        body=f'''<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
        <IsTruncated>{str(truncated).lower()}</IsTruncated>
        <NextContinuationToken>next</NextContinuationToken>
        <Contents><Key>EDDE_V2/{len(calls)}.nc</Key><Size>4</Size>
        <ETag>one</ETag><LastModified>today</LastModified></Contents></ListBucketResult>'''
        response=Response(b'')
        response.content=body.encode()
        return response
    monkeypatch.setattr(client.session,'get',get)
    objects,_=client.listing('EDDE_V2/test/')
    assert len(objects)==2
    assert 'continuation-token' not in calls[0]
    assert calls[1]['continuation-token']=='next'
    assert objects[1]['key']=='EDDE_V2/2.nc'


def test_reject_mixed_units_across_months(tmp_path,monkeypatch):
    client=client_fixture(tmp_path,monkeypatch)
    other=tmp_path/'other.nc'
    make_data(other)
    with netCDF4.Dataset(other,'a') as ds:ds['PRECIP'].units='kg m-2 s-1'
    first=client.inventory('m','s',2000)[0]
    second=dict(first,key=first['key'].replace('2000-01','2000-02'))
    monkeypatch.setattr(client,'inventory',lambda *a:[first,second])
    monkeypatch.setattr(client,'fetch',lambda obj:(tmp_path/'data.nc' if obj==first else other,{'source':obj}))
    with pytest.raises(DataQualityError,match='Inconsistent metadata'):
        client.query([Point('a',0,0)],'WRF-MPI','Historical','2000-01-01','2000-02-02',['prday'])
