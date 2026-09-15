"""Authorized, basin-derived network preparation; never rebuild shared soils.

CLI runs in a dedicated main-thread process so network/native deadlines are
enforceable. Inputs are retained as ordinary project artifacts, not activated.
"""
from datetime import datetime, timezone
import json
import math
import multiprocessing
import re
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.io import FilePath
from rasterio.enums import ColorInterp
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds

from . import rainfall_io as io
from .soil_inputs import SOURCE_ID, _json_snapshot, dependency_state
from .soil_snapshot import source_state
from .source_preparation import prepare_local_sources
from .source_transport import Transport, RangeFile, deadline, THICK_URL, SDA_URL

__all__ = ['acquire_sources']
FIELDS = ['mukey','areatypename','areasymbol','saversion','saverest']


def _lineage_request(keys):
    # Keys come from bounded original raster admission, never SQL fragments.
    if any(not isinstance(k,str) or not k.isascii() or not k.isdecimal() or int(k) <= 0 for k in keys):
        raise ValueError('Invalid original map-unit keys')
    query = ('SELECT mu.mukey,l.areatypename,l.areasymbol,sac.saversion,sac.saverest '
             'FROM mapunit mu INNER JOIN legend l ON l.lkey=mu.lkey '
             'INNER JOIN sacatalog sac ON sac.areasymbol=l.areasymbol WHERE mu.mukey IN ('
             +','.join("'"+k+"'" for k in keys)+') ORDER BY mu.mukey')
    request = {'query':query,'format':'JSON+COLUMNNAME'}
    raw = json.dumps(request).encode()
    if len(raw) > io.MAX_TEXT:
        raise ValueError('Encoded SDA request exceeds 1 MiB')
    return request,raw


def _lineage(keys, output):
    if not keys:
        io.write_json(output/'sda_skipped.json',{'reason':'no_usable_original_keys'})
        return None
    request,raw = _lineage_request(keys)
    io.write_json(output/'sda_query.json',request)
    folder = output/'sda_requests'; folder.mkdir()
    transport = Transport(folder,seconds=30,limit=io.MAX_TEXT)
    _,body = transport.request(SDA_URL,method='POST',data=raw,
                               headers={'Content-Type':'application/json'},limit=io.MAX_TEXT)
    response = output/'sda_response.json'
    with response.open('xb') as stream: stream.write(body)
    return _catalog_from_response(keys,response,output,datetime.now(timezone.utc).isoformat())


def _catalog_from_response(keys, response, output, retrieved_at):
    record,response_hash = _json_snapshot(response)
    if set(record) != {'Table'}:
        raise ValueError('Unexpected SDA response/error')
    rows = record['Table']
    if not isinstance(rows,list) or not rows or rows[0] != FIELDS:
        raise ValueError('Unexpected SDA lineage columns')
    associations,versions = {},{}
    for row in rows[1:]:
        if not isinstance(row,list) or len(row) != len(FIELDS) or not all(isinstance(v,str) for v in row):
            raise ValueError('Malformed SDA lineage row')
        key,area_type,symbol,version,rest = row
        if key not in keys or key in versions:
            raise ValueError('Unexpected or duplicate SDA map unit')
        if not version.strip() or not rest.strip():
            raise ValueError('Missing current survey identity')
        if area_type == 'Non-MLRA Soil Survey Area' and re.fullmatch(r'[A-Z]{2}[0-9]{3}',symbol):
            associations[key] = 'SSURGO'
        elif area_type == 'Country' and symbol == 'US':
            associations[key] = 'STATSGO'
        else:
            raise ValueError('Unrecognized survey collection identity')
        versions[key] = {'areasymbol':symbol,'current_survey_version':version,'current_survey_date':rest,
                         'cached_horizon_survey_version':'unknown'}
    catalog = output/'collection_catalog.json'
    io.write_json(catalog,dict(schema_version=1,collection_by_mukey=associations,source=SDA_URL,
        retrieved_at=retrieved_at,current_versions=versions,
        response_sha256=response_hash))
    return catalog


def _native_window(grid, output, *, transport_factory=Transport):
    folder = output/'thick_requests'; folder.mkdir()
    transport = transport_factory(folder)
    native = output/'native_thick.tif'
    with deadline(120):
        source = RangeFile(transport)
        with FilePath(source) as bridge, bridge.open(driver='GTiff') as ds:
            if (ds.count != 1 or ds.crs is None or ds.units[0] not in (None,'','inch','inches','in')
                    or ds.scales != (1.0,) or ds.offsets != (0.0,)
                    or ds.tags().get('AREA_OR_POINT','Area') != 'Area'
                    or np.dtype(ds.dtypes[0]).kind not in 'iuf' or ds.dtypes[0] in ('int64','uint64')
                    or np.dtype(ds.dtypes[0]).itemsize > 8
                    or ds.colorinterp[0] not in (ColorInterp.gray,ColorInterp.undefined)
                    or any(r*c > 10_000_000 for r,c in ds.block_shapes)):
                raise ValueError('Unexpected original THICK raster metadata')
            if ds.transform.b or ds.transform.d or ds.transform.a <= 0 or ds.transform.e >= 0:
                raise ValueError('Unsupported native THICK grid')
            rows,cols = grid['shape']
            affine = rasterio.Affine(*grid['transform'])
            left,top = affine*(0,0); right,bottom = affine*(cols,rows)
            bounds = transform_bounds(grid['crs'],ds.crs,left,bottom,right,top)
            floating = from_bounds(*bounds,transform=ds.transform)
            col,row = math.floor(floating.col_off),math.floor(floating.row_off)
            end_col,end_row = math.ceil(floating.col_off+floating.width),math.ceil(floating.row_off+floating.height)
            width,height = end_col-col,end_row-row
            if col < 0 or row < 0 or end_col > ds.width or end_row > ds.height or not 0 < width*height <= 10_000_000:
                raise ValueError('Basin native window is outside coverage or exceeds raster limit')
            window = Window(col,row,width,height)
            values = ds.read(1,window=window,masked=True)
            if source.failure is not None: raise source.failure
            profile = ds.profile.copy()
            profile.update(width=width,height=height,transform=ds.window_transform(window),compress='deflate')
            nodata = ds.nodata
            if nodata is not None and not math.isfinite(nodata):
                nodata = 'NaN' if math.isnan(nodata) else 'Infinity' if nodata > 0 else '-Infinity'
            source_metadata = {'grid':{'shape':list(ds.shape),'crs':str(ds.crs),'transform':list(ds.transform)[:6]},
                               'nodata':nodata,'units':ds.units[0],'window':[col,row,width,height]}
            with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
                with rasterio.open(native,'w',**profile) as target:
                    target.write(values.filled(ds.nodata if ds.nodata is not None else 0),1)
                    target.write_mask((~np.ma.getmaskarray(values)).astype('uint8')*255)
                    target.set_band_unit(1,'inch')
        source.verify()
        digest = io.digest(native,io.MAX_PREDICTOR_BYTES)
        with rasterio.open(native) as ds:
            native_grid = {'shape':list(ds.shape),'crs':str(ds.crs),'transform':list(ds.transform)[:6]}
            bounds = list(ds.bounds)
        evidence = output/'native_evidence.json'
        replay = getattr(transport,'retrieval_mode',None) == 'retained_transcript'
        io.write_json(evidence,dict(schema_version=1,source_id=SOURCE_ID,source=THICK_URL,sha256=digest,
            grid=native_grid,bounds=bounds,object_identity=list(source.identity),source_metadata=source_metadata,
            transferred_bytes=transport.received,requests=transport.requests,units='inch',
            retrieval_mode='retained_transcript' if replay else 'network',
            network_requests=0 if replay else transport.requests,
            replayed_at=datetime.now(timezone.utc).isoformat() if replay else None,
            retrieved_at=None if replay else datetime.now(timezone.utc).isoformat()))
    return native,evidence


def _acquisition_worker(operation, target, arguments, output, active):
    from contextlib import redirect_stderr, redirect_stdout
    import traceback
    from . import source_transport
    source_transport._ACTIVE_DEADLINE = active
    with (output/f'{operation}_worker.log').open('x') as log, redirect_stdout(log), redirect_stderr(log):
        try:
            target(*arguments,output)
        except Exception as exc:  # noqa: BLE001 -- dedicated process boundary; retains failure and re-raises.
            # Dedicated process boundary: all failures retain diagnostics;
            # the supervising parent rejects a nonzero worker exit.
            io.write_json(output/f'{operation}_failure.json',{'status':'failed','error_type':type(exc).__name__,
                                                       'error':str(exc)[:2048]})
            traceback.print_exc(limit=10)
            raise


def _supervise(operation, target, arguments, output, timeout):
    if not 0 < timeout <= 120:
        raise ValueError('Native acquisition deadline must be at most 120 seconds')
    io.write_json(output/f'{operation}_started.json',{'status':'started','timeout_seconds':timeout})
    # Linux worker isolation is already the runtime baseline. Unlike SIGALRM,
    # this watchdog also interrupts GDAL while it has not returned to Python.
    context = multiprocessing.get_context('fork')
    active = context.Value('d',0,lock=False)
    process = context.Process(target=_acquisition_worker,args=(operation,target,arguments,output,active))
    until = time.monotonic()+timeout
    process.start()
    while process.is_alive():
        now = time.monotonic()
        request_until = active.value
        if now >= until or (request_until and now >= request_until):
            break
        process.join(min(.02,until-now))
    if process.is_alive():
        process.kill()
        process.join(5)
        io.write_json(output/f'{operation}_timeout.json',{'status':'failed','reason':'deadline_exceeded',
                                                  'worker_stopped':not process.is_alive()})
        raise TimeoutError('Source acquisition exceeded its wall deadline')
    if process.exitcode != 0:
        raise ValueError(f'Source acquisition failed; inspect {operation}_worker.log and retained request diagnostics')


def _supervised_native(grid, output, *, timeout=120):
    _supervise('native',_native_window,(grid,),output,timeout)
    return output/'native_thick.tif',output/'native_evidence.json'


def acquire_sources(wd, dem, mask):
    """Acquire approved assets and return a verified local receipt, without promotion."""
    initial = prepare_local_sources(wd,dem,mask)
    record,_ = _json_snapshot(initial)
    output = initial.parent/'acquisition'; output.mkdir()
    io.write_json(output/'incomplete.json',{'status':'incomplete'})
    _supervise('sda',_lineage,(record['mukeys'],),output,30)
    catalog = output/'collection_catalog.json' if record['mukeys'] else None
    native,evidence = _supervised_native(record['grid'],output)
    return _finish_preparation(wd,dem,mask,record,output,catalog,native,evidence)


def _finish_preparation(wd, dem, mask, record, output, catalog, native, evidence):
    if dependency_state(record['dependency_state']) != record['dependency_state']:
        raise ValueError('Project inputs changed during source acquisition')
    identity = record['cache_identity']
    if identity is not None and source_state(Path(wd)/'soils/ssurgo_tabular_cache.sqlite') != identity['source_state']:
        raise ValueError('Soil cache changed during source acquisition')
    receipt = prepare_local_sources(wd,dem,mask,collection_catalog=catalog,thick=native,thick_evidence=evidence)
    prepared,_ = _json_snapshot(receipt)
    if any(prepared['dependency_state'].get(k) != v for k,v in record['dependency_state'].items()):
        raise ValueError('Project inputs changed before final source preparation')
    if prepared['cache_identity'] != identity:
        raise ValueError('Soil cache changed before final source preparation')
    if prepared['mukeys'] != record['mukeys'] or prepared['grid'] != record['grid']:
        raise ValueError('Basin keys/grid changed before final source preparation')
    io.write_json(output/'complete.json',{'status':'complete','prepared_receipt':str(receipt),
                                        'prepared_receipt_sha256':io.digest(receipt,io.MAX_TEXT)})
    (output/'incomplete.json').unlink()
    return receipt


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    parser.add_argument('--dem',type=Path,required=True)
    parser.add_argument('--mask',type=Path,required=True)
    args = parser.parse_args()
    print(acquire_sources(args.project,args.dem,args.mask))
