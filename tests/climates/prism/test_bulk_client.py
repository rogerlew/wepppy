"""PRISM protocol/cache regressions using real filesystem artifacts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import gzip
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import requests

from wepppy.climates.prism.bulk_client import (
    PrismBulkClient, PrismCacheError, PrismCoverageError, PrismError,
    PrismFreshnessError, PrismProtocolError, snap,
)
from wepppy.climates.prism._bulk_protocol import (
    COLUMNS, GEOMETRY, VARIABLES, PrismCell, parse_bulk, parse_release,
)
from wepppy.climates.prism._bulk_transport import BulkTransport

pytestmark = pytest.mark.unit
START, END = date(2020, 1, 1), date(2020, 1, 3)
POINTS = {'palouse': (-116.5, 46.5)}
EVIDENCE = Path(__file__).resolve().parents[3] / 'docs/investigations/20261008_prism_800m_bulk/evidence'
# Actual retained observations, reduced to three days; native source values stay exact.
SOURCE = EVIDENCE / 'sample_2020.csv.gz'


def source_csv(cells, start=START, end=END):
    source = pd.read_csv(SOURCE, compression='gzip', skiprows=10)
    sub = source[(source.Name == 'palouse') & (source.Date >= str(start)) & (source.Date <= str(end))].copy()
    frames = []
    for cell in cells:
        frame = sub.copy()
        frame['Name'] = cell.id
        frame['Longitude'], frame['Latitude'] = cell.center
        frames.append(frame)
    header = f'PRISM Time Series Data\nSpatial resolution: 800m\nGrid Cell Interpolation: Off\nPeriod: {start} - {end}\n'
    return (header + pd.concat(frames).to_csv(index=False)).encode()


def release(variable, start=START, end=END, version='2024-12-17'):
    return [[str(d.date()), version, variable, '8',
             f'https://services.nacse.org/prism/data/get/us/800m/{variable}/{d:%Y%m%d}']
            for d in pd.date_range(start, end)]


class Provider:
    """Replay server boundaries; production parser, locks and writers execute."""
    def __init__(self):
        self.version = '2024-12-17'
        self.bulk_calls = 0
        self.manifest_calls = 0
        self.mutate = lambda value: value
        self.error_manifest = False
        self.change_during_bulk = False
        self.pending_cells = []

    def request(self, method, url, *, data, **kwargs):
        if 'releaseDate' in url:
            self.manifest_calls += 1
            variable = url.split('/')[-3]
            raw = b'provider error' if self.error_manifest else json.dumps(release(variable, version=self.version)).encode()
        elif method == 'POST':
            self.bulk_calls += 1
            self.pending_cells = [PrismCell(int(name[1:].split('c')[0]), int(name.split('c')[1])) for name in data['names'].split('|')]
            if self.change_during_bulk:
                self.version = '2024-12-18' if self.version == '2024-12-17' else '2024-12-17'
            raw = b'{"result":{"csv":"ticket/test.csv"},"errors":false}'
        else:
            raw = self.mutate(source_csv(self.pending_cells))
        response = requests.Response()
        response.status_code = 200
        response._content = raw
        response._content_consumed = True
        return response


@pytest.fixture
def provider():
    return Provider()


def test_configuration_and_env(tmp_path, monkeypatch):
    monkeypatch.delenv('PRISM_CACHE_DIR', raising=False)
    with pytest.raises(ValueError, match='PRISM_CACHE_DIR'):
        PrismBulkClient()
    with pytest.raises(ValueError):
        PrismBulkClient('relative')
    monkeypatch.setenv('PRISM_CACHE_DIR', str(tmp_path))
    assert PrismBulkClient().cache.root.is_relative_to(tmp_path)


def test_native_grid_edges_and_aliases():
    cell = snap(-116.5, 46.5)
    assert snap(*cell.center, source_crs='EPSG:4269') == cell
    assert snap(cell.center[0]+.001, cell.center[1]-.001) == cell
    edge = (GEOMETRY['x0']+10*GEOMETRY['dx'], GEOMETRY['y0']+20*GEOMETRY['dy'])
    assert snap(*edge, source_crs='EPSG:4269') == PrismCell(20, 10)
    assert snap(GEOMETRY['x0'], GEOMETRY['y0'], source_crs='EPSG:4269') == PrismCell(0,0)
    for lon,lat in [(GEOMETRY['x0']+7025*GEOMETRY['dx'],40),(-110,GEOMETRY['y0']+3105*GEOMETRY['dy']), (0,0)]:
        with pytest.raises(PrismCoverageError):
            snap(lon,lat,source_crs='EPSG:4269')
    for lon in [float('nan'), float('inf'), 181]:
        with pytest.raises(ValueError):
            snap(lon,40)


def test_recorded_bulk_leap_year_and_masked_cells():
    raw = gzip.decompress(SOURCE.read_bytes())
    locations = json.loads((EVIDENCE/'locations.json').read_text())
    # Original fixture uses friendly names. Rewrite only names to native IDs,
    # dropping same-cell aliases to model client deduplication before submit.
    frame = pd.read_csv(SOURCE, compression='gzip', skiprows=10)
    chosen = []; seen = set()
    for item in locations:
        cell = PrismCell(item['row'],item['col'])
        if cell in seen or item['name'] not in set(frame.Name):
            continue
        seen.add(cell);chosen.append((item['name'],cell))
    subset = frame[frame.Name.isin([name for name,_ in chosen])].copy()
    subset.Name = subset.Name.map({name:c.id for name,c in chosen})
    header = raw.decode().split('Name,Longitude,Latitude')[0]
    parsed = parse_bulk((header+subset.to_csv(index=False)).encode(),[c for _,c in chosen],date(2020,1,1),date(2020,12,31))
    assert all(len(f)==366 and pd.Timestamp('2020-02-29') in f.index for f in parsed.values())
    assert parsed[snap(-116.5,46.5).id].iloc[0].ppt == 14.62
    assert any((f.tdmean<f.tmin).any() for f in parsed.values())
    with pytest.raises(PrismCoverageError):
        parse_bulk((header+subset.to_csv(index=False)).encode(),[c for _,c in chosen]+[PrismCell(0,0)],date(2020,1,1),date(2020,12,31))


@pytest.mark.parametrize('mutation', ['missing_date','duplicate','nonfinite','sentinel','negative_p','negative_solar','reversed_temp','wrong_units','wrong_cell','wrong_center'])
def test_invalid_payload_not_published(tmp_path,provider,mutation):
    def mutate(raw):
        head,table=raw.decode().split('Name,Longitude,Latitude',1)
        frame=pd.read_csv(__import__('io').StringIO('Name,Longitude,Latitude'+table))
        if mutation=='missing_date': frame=frame.iloc[:-1]
        elif mutation=='duplicate': frame=pd.concat([frame,frame.iloc[:1]])
        elif mutation=='nonfinite': frame.loc[0,COLUMNS[0]]=float('inf')
        elif mutation=='sentinel': frame.loc[0,COLUMNS[3]]=-9999
        elif mutation=='negative_p': frame.loc[0,COLUMNS[0]]=-1
        elif mutation=='negative_solar': frame.loc[0,COLUMNS[-1]]=-1
        elif mutation=='reversed_temp': frame.loc[0,COLUMNS[1]]=80
        elif mutation=='wrong_units': frame=frame.rename(columns={COLUMNS[0]:'ppt (inch)'})
        elif mutation=='wrong_cell': frame.Name='wrong'
        elif mutation=='wrong_center': frame.Longitude=0
        return (head+frame.to_csv(index=False)).encode()
    provider.mutate=mutate
    client=PrismBulkClient(tmp_path,session=provider)
    with pytest.raises(PrismError):client.retrieve(POINTS,START,END)
    assert not list(client.cache.root.glob('entries/**/*.json'))
    attempt=next((client.cache.root/'attempts').iterdir())
    assert (attempt/'bulk.csv.gz').exists()
    assert json.loads((attempt/'status.json').read_text())['state']=='failed'


def test_cold_warm_alias_raw_units_and_revision_invalidation(tmp_path,provider):
    client=PrismBulkClient(tmp_path,session=provider)
    points=dict(POINTS,alias=(-116.499,46.501))
    cold=client.retrieve(points,START,END)
    assert len(cold.frames)==1 and provider.bulk_calls==1
    frame=next(iter(cold.frames.values()))
    assert frame.iloc[0].ppt==14.62 and frame.iloc[0].soltotal==1.16
    assert frame.iloc[2].tdmean < frame.iloc[2].tmin
    warm=client.retrieve(POINTS,START,END)
    pd.testing.assert_frame_equal(frame,next(iter(warm.frames.values())))
    assert provider.bulk_calls==1 and provider.manifest_calls==15
    assert warm.provenance[0]['cache_hit']
    old=Path(cold.provenance[0]['source_directory'])
    provider.version='2024-12-16'  # Any inequality, not only newer dates.
    fresh=client.retrieve(POINTS,START,END)
    assert provider.bulk_calls==2 and not fresh.provenance[0]['cache_hit']
    assert old.exists() and old!=Path(fresh.provenance[0]['source_directory'])


def test_missing_manifest_never_serves_warm_data(tmp_path,provider):
    client=PrismBulkClient(tmp_path,session=provider)
    client.retrieve(POINTS,START,END)
    provider.error_manifest=True
    with pytest.raises(PrismFreshnessError):client.retrieve(POINTS,START,END)
    assert provider.bulk_calls==1


def test_revision_race_bounded_and_not_published(tmp_path,provider):
    provider.change_during_bulk=True
    client=PrismBulkClient(tmp_path,session=provider)
    with pytest.raises(PrismFreshnessError,match='changed'):client.retrieve(POINTS,START,END)
    assert provider.bulk_calls==2
    assert not list(client.cache.root.glob('entries/**/*.json'))
    assert len(list(client.cache.root.glob('attempts/*/bulk.csv.gz')))==2


def test_corrupt_cache_fails_explicitly(tmp_path,provider):
    client=PrismBulkClient(tmp_path,session=provider)
    result=client.retrieve(POINTS,START,END)
    ref=result.provenance[0]
    (Path(ref['source_directory'])/f"{ref['cell']}.parquet").write_bytes(b'corrupt')
    with pytest.raises(PrismCacheError,match='checksum'):client.retrieve(POINTS,START,END)
    assert provider.bulk_calls==1


def test_interrupted_publication_preserves_evidence_and_retries(tmp_path,provider):
    client=PrismBulkClient(tmp_path,session=provider)
    with patch('wepppy.climates.prism._bulk_cache.os.replace',side_effect=OSError('disk failure')):
        with pytest.raises(OSError,match='disk failure'):client.retrieve(POINTS,START,END)
    assert not list(client.cache.root.glob('entries/**/*.json'))
    assert list(client.cache.root.glob('attempts/*/*.parquet'))
    client.retrieve(POINTS,START,END)
    assert provider.bulk_calls==2


def test_concurrent_same_partition_deduplicates_acquisition(tmp_path,provider):
    a=PrismBulkClient(tmp_path,session=provider)
    b=PrismBulkClient(tmp_path,session=provider)
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda c:c.retrieve(POINTS,START,END),[a,b]))
    assert provider.bulk_calls==1
    pd.testing.assert_frame_equal(next(iter(results[0].frames.values())),next(iter(results[1].frames.values())))


def test_lock_wait_is_bounded(tmp_path,provider):
    a=PrismBulkClient(tmp_path,session=provider)
    b=PrismBulkClient(tmp_path,session=provider,lock_timeout=.01)
    with a.cache.lock(f'{START}_{END}'):
        with pytest.raises(TimeoutError,match='lock'):b.retrieve(POINTS,START,END)
    assert provider.bulk_calls==0


@pytest.mark.parametrize('value', ['bad json', '[]', '{}', '[["2020-01-01","2024-01-01","wrong",8,"url"]]'])
def test_manifest_errors(value):
    with pytest.raises(PrismFreshnessError):parse_release(value,'ppt',START,END)


@pytest.mark.parametrize('path', ['https://attacker/a.csv','../a.csv','/a.csv','ticket/../../a.csv'])
def test_download_path_is_provider_relative(tmp_path,path):
    transport=BulkTransport()
    with patch.object(transport,'request',return_value=json.dumps({'result':{'csv':path}}).encode()):
        with pytest.raises(PrismProtocolError,match='path'):transport.extract([snap(-116.5,46.5)],START,END,tmp_path)


def test_batch_and_year_partition_limits(tmp_path):
    client=PrismBulkClient(tmp_path)
    cells=[PrismCell(100,100+i) for i in range(501)]
    points={c.id:c.center for c in cells}
    calls=[]
    def fake(cells,start,end):
        calls.append((len(cells),start,end))
        return {c.id:pd.DataFrame(index=pd.date_range(start,end)) for c in cells},[]
    with patch.object(client,'_attempt',side_effect=fake):
        client.retrieve(points,'2019-12-31','2020-01-03',source_crs='EPSG:4269')
    assert calls==[(500,date(2019,12,31),date(2019,12,31)),(1,date(2019,12,31),date(2019,12,31)),(500,START,END),(1,START,END)]


def test_second_reference_failure_keeps_first_valid_and_retry_fills_missing(tmp_path,provider):
    import wepppy.climates.prism._bulk_cache as cache_module
    client=PrismBulkClient(tmp_path,session=provider)
    first=snap(-116.5,46.5);second=PrismCell(first.row,first.col+1)
    points={'first':first.center,'second':second.center}
    original=cache_module.os.replace
    count=0
    def interrupt(source,target):
        nonlocal count
        count+=1
        if count==2:raise OSError('second reference failed')
        return original(source,target)
    with patch.object(cache_module.os,'replace',side_effect=interrupt):
        with pytest.raises(OSError,match='second reference'):
            client.retrieve(points,START,END,source_crs='EPSG:4269')
    assert len(list(client.cache.root.glob('entries/**/*.json')))==1
    result=client.retrieve(points,START,END,source_crs='EPSG:4269')
    assert len(result.frames)==2 and sum(p['cache_hit'] for p in result.provenance)==1
    assert len(provider.pending_cells)==1


def test_single_revision_race_retries_successfully(tmp_path,provider):
    original=provider.request
    def request(*args,**kwargs):
        if args[0]=='POST' and provider.bulk_calls==0:provider.version='2024-12-18'
        return original(*args,**kwargs)
    provider.request=request
    result=PrismBulkClient(tmp_path,session=provider).retrieve(POINTS,START,END)
    assert provider.bulk_calls==2 and len(result.frames)==1


def test_poll_response_uses_ticket_and_retains_evidence(tmp_path):
    responses=[{'gricket':'ticket123','delay':{'status':'processing'},'errors':False},
               {'result':{'csv':'ticket123/data.csv'},'errors':False}]
    calls=[]
    class Session:
        def request(self,method,url,**kwargs):
            calls.append((method,url,kwargs))
            r=requests.Response();r.status_code=200
            r._content=json.dumps(responses.pop(0)).encode() if method=='POST' else b'raw csv'
            r._content_consumed=True
            return r
    transport=BulkTransport(Session(),poll_seconds=.001)
    assert transport.extract([snap(-116.5,46.5)],START,END,tmp_path)==b'raw csv'
    assert calls[1][2]['data']['gricket']=='ticket123'
    assert all(c[2]['headers']['Connection']=='close' for c in calls)
    assert (tmp_path/'submit.json').exists() and (tmp_path/'poll-0.json').exists()


def test_poll_deadline_and_malformed_response(tmp_path):
    transport=BulkTransport(poll_seconds=.001,job_timeout=.001)
    with patch.object(transport,'request',return_value=b'not json'):
        with pytest.raises(PrismProtocolError,match='Non-JSON'):
            transport.extract([snap(-116.5,46.5)],START,END,tmp_path)
    with patch.object(transport,'request',return_value=b'{"gricket":"abc","delay":{}}'):
        with pytest.raises(TimeoutError,match='timed out'):
            transport.extract([snap(-116.5,46.5)],START,END,tmp_path)


def test_http_failure_and_body_limit(tmp_path):
    class Session:
        def request(self,*args,**kwargs):
            r=requests.Response();r.status_code=200;r._content=b'too much';r._content_consumed=True
            return r
    with pytest.raises(PrismProtocolError,match='exceeds'):
        BulkTransport(Session()).request('GET','https://example.test',tmp_path/'http.json',limit=2)
    with patch.object(Session,'request',side_effect=requests.ConnectionError('failed')):
        with pytest.raises(PrismError,match='HTTP request failed'):
            BulkTransport(Session()).request('GET','https://example.test',tmp_path/'http.json')


def test_release_metadata_count_and_inventory():
    value=release('ppt');value[0][3]='7'
    assert parse_release(json.dumps(value),'ppt',START,END)['2020-01-01'][1]==7
    for rows in [value+value[:1],value[:-1]]:
        with pytest.raises(PrismFreshnessError):parse_release(json.dumps(rows),'ppt',START,END)


@pytest.mark.parametrize('value',[float('nan'),float('inf'),0,-1])
def test_nonfinite_or_unbounded_wait_configuration(tmp_path,value):
    with pytest.raises(ValueError):PrismBulkClient(tmp_path,lock_timeout=value)
    with pytest.raises(ValueError):BulkTransport(job_timeout=value)
    with pytest.raises(ValueError):BulkTransport(poll_seconds=value)
