"""Replay a completed bounded HTTP transcript without any network connection.

Used to recover retained acquisition data after local receipt serialization
failure. Original attempts remain immutable; every replay input is hash-pinned.
"""
import io as bytesio
import hashlib
from pathlib import Path
import time

from . import rainfall_io as io
from .soil_inputs import _json_snapshot
from .source_transport import Transport, THICK_URL, MAX_BODY

__all__ = ['ReplayTransport']


class _Response(bytesio.BytesIO):
    def __init__(self, body, record):
        super().__init__(body)
        self.headers = record['response_headers']
        self.status = record['http_status']
    def geturl(self): return THICK_URL


class ReplayTransport(Transport):
    retrieval_mode = 'retained_transcript'
    def __init__(self, original, output):
        # Do not even construct a network opener during offline recovery.
        self.output,self.until,self.limit = output,time.monotonic()+120,MAX_BODY
        self.received,self.requests = 0,0
        files = sorted(original.glob('request-[0-9][0-9][0-9][0-9][0-9].json'))
        if not 2 <= len(files) <= 1539:
            raise ValueError('Invalid bounded range transcript length')
        self.records,self.hashes = [],{}
        received = 0
        for path in files:
            record,digest = _json_snapshot(path)
            if record.get('status') != 'complete' or record.get('url') != THICK_URL:
                raise ValueError('Only complete original-object requests may be replayed')
            self.hashes[str(path)] = digest
            body = path.with_suffix('.body') if record['method'] == 'GET' else None
            if body is not None:
                self.hashes[str(body)] = io.digest(body,65536)
                if record.get('body_sha256',self.hashes[str(body)]) != self.hashes[str(body)]:
                    raise ValueError('Retained range body differs from acquisition hash')
                received += io.regular(body,65536).stat().st_size
            self.records.append((record,body))
        if received > MAX_BODY:
            raise ValueError('Retained transcript exceeds acquisition budget')
        self.index = 0
        self.opener = self
        io.write_json(output/'replay_sources.json',{'sources_sha256':self.hashes,'network_requests':0})

    def open(self, request, **kwargs):
        if self.index >= len(self.records):
            raise ValueError('Replay requested bytes absent from retained transcript')
        record,path = self.records[self.index]
        self.index += 1
        actual = {k.lower():v for k,v in request.header_items() if k.lower() != 'accept-encoding'}
        expected = {k.lower():v for k,v in record['headers'].items()}
        if request.full_url != THICK_URL or request.method != record['method'] or actual != expected:
            raise ValueError('Replay request differs from retained request')
        body = b''
        if path is not None:
            with io.open_local(path,65536) as stream:
                body = stream.read(65537)
            if hashlib.sha256(body).hexdigest() != self.hashes[str(path)]:
                raise ValueError('Retained range body changed')
            if len(body) != record['received_bytes']:
                raise ValueError('Retained range body length differs')
        return _Response(body,record)

    def complete(self):
        if self.index != len(self.records):
            raise ValueError('Replay did not consume the complete original transcript')
        io.recheck(self.hashes,limits={p:65536 if p.endswith('.body') else io.MAX_TEXT for p in self.hashes})


def replay_native(grid, original, output):
    """Re-decode a retained transcript; no network fallback is possible."""
    from .source_acquisition import _native_window
    transports = []
    def factory(folder):
        transport = ReplayTransport(original,folder)
        transports.append(transport)
        return transport
    native,evidence = _native_window(grid,output,transport_factory=factory)
    transports[0].complete()
    return native,evidence


def recover_sources(wd, dem, mask, original_receipt, *, expected_sha256):
    """Prepare fresh local inputs from an intact failed acquisition transcript."""
    from .source_acquisition import _supervise, _finish_preparation, _lineage_request, _catalog_from_response
    from .source_preparation import _inside, prepare_local_sources
    root = Path(wd).absolute()
    original_receipt = _inside(root,original_receipt)
    original,digest = _json_snapshot(original_receipt)
    if digest != expected_sha256 or original.get('project') != str(root) or original.get('status') != 'complete':
        raise ValueError('Original acquisition receipt identity differs')
    original_output = original_receipt.parent/'acquisition'
    initial = prepare_local_sources(root,dem,mask)
    record,_ = _json_snapshot(initial)
    for key in ('grid','mukeys','dependency_state','cache_identity'):
        if original[key] != record[key]:
            raise ValueError('Project inputs changed since retained acquisition')
    output = initial.parent/'recovery'; output.mkdir()
    io.write_json(output/'incomplete.json',{'status':'incomplete'})
    catalog = None
    if record['mukeys']:
        lineage,_ = _json_snapshot(original_output/'collection_catalog.json')
        if lineage.get('response_sha256') != io.digest(original_output/'sda_response.json',io.MAX_TEXT):
            raise ValueError('Retained lineage response differs')
        request,_ = _json_snapshot(original_output/'sda_query.json')
        if request != _lineage_request(record['mukeys'])[0]:
            raise ValueError('Retained lineage query differs from this basin')
        catalog = _catalog_from_response(record['mukeys'],original_output/'sda_response.json',output,
                                         lineage['retrieved_at'])
        rebuilt,_ = _json_snapshot(catalog)
        if rebuilt != lineage:
            raise ValueError('Retained lineage catalog differs from its response')
    native_hash = io.digest(original_output/'native_thick.tif',io.MAX_PREDICTOR_BYTES)
    io.write_json(output/'recovery_sources.json',{'original_receipt':str(original_receipt),
                  'original_receipt_sha256':digest,'original_native_sha256':native_hash,'network_requests':0})
    _supervise('native',replay_native,(record['grid'],original_output/'thick_requests'),output,120)
    # Early transcripts predate per-response hashes. Require agreement with
    # the independently retained, fully decoded original native output too.
    if any(io.digest(p,io.MAX_PREDICTOR_BYTES) != native_hash for p in
           (output/'native_thick.tif',original_output/'native_thick.tif')):
        raise ValueError('Replayed native output differs from original decoded raster')
    return _finish_preparation(root,dem,mask,record,output,catalog,
                               output/'native_thick.tif',output/'native_evidence.json')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    parser.add_argument('--dem',type=Path,required=True)
    parser.add_argument('--mask',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--sha256',required=True)
    args = parser.parse_args()
    print(recover_sources(args.project,args.dem,args.mask,args.receipt,expected_sha256=args.sha256))
