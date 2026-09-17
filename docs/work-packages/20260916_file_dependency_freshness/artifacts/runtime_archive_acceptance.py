"""After-restart native Geneva archive/browse acceptance on a unique new project.

No named-project writes, existing project reset, auth bypass or service restart.
Canonical owner helpers run with the container's normal UID/GID/umask. Optional
real recorder seed roots are read-only controls, never relocated into the run.
Live HTTP authorization/RQ transport and profile repository archival are separate.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
from types import SimpleNamespace
from uuid import uuid4
import zipfile


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def inventory(root):
    records = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if relative.parts[0] == 'archives' or str(relative) == '.config-amendment.lock':
            continue
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise AssertionError(f'Unexpected disposable fixture symlink: {relative}')
        records[str(relative)] = {'directory': path.is_dir(),
                                 'mode': stat.S_IMODE(info.st_mode)}
        if path.is_file():
            records[str(relative)].update(size=info.st_size, sha256=sha(path))
    return records


async def browse_records(root, records):
    from wepppy.microservices.browse.listing import get_page_entries
    from wepppy.microservices.browse._download import download_response_file
    directories = {Path(relative).parent for relative in records}
    observed = {}
    for relative in sorted(directories):
        entries, total, _ = await get_page_entries(str(root), str(root / relative), page_size=1000)
        names = {item[0] for item in entries}
        expected = {Path(name).name for name in records if Path(name).parent == relative}
        assert expected <= names, (str(relative), expected - names)
        observed[str(relative)] = {'names': sorted(names), 'total': total}
    for relative, record in records.items():
        if record['directory']:
            continue
        response = await download_response_file(str(root / relative), {})
        digest = hashlib.sha256()
        statuses = []

        async def send(message):
            if message['type'] == 'http.response.start':
                statuses.append(message['status'])
            elif message['type'] == 'http.response.body':
                digest.update(message.get('body', b''))

        async def receive():
            return {'type': 'http.request', 'body': b'', 'more_body': False}

        await response({'type': 'http', 'method': 'GET', 'headers': [], 'extensions': {}}, receive, send)
        assert statuses == [200] and digest.hexdigest() == record['sha256'], relative
    return observed


def profiles(seed_roots):
    from requests.exceptions import RequestException
    from wepppy.profile_recorder.sbs_seed import read_event_seed
    result = {}
    for supplied in seed_roots:
        root = Path(supplied).resolve(strict=True)
        events = {}
        for status_path in sorted((root / 'sbs/events').glob('*/status.json')):
            status = json.loads(status_path.read_text())
            event_id = status['event_id']
            if status['status'] == 'complete':
                seed = read_event_seed(root, event_id, required=True)
                events[event_id] = {'status': 'complete', 'name': seed.name,
                                    'sha256': hashlib.sha256(seed.payload).hexdigest()}
            else:
                try:
                    read_event_seed(root, event_id, required=True)
                except RequestException:
                    events[event_id] = {'status': status['status'], 'replay_rejected': True}
                else:
                    raise AssertionError('Incomplete event became an accepted receipt')
        assert events, f'No event records at explicitly selected seed root {root}'
        result[str(root)] = {'events': events, 'inventory': inventory(root),
                             'scope': 'external recorder repository; read-only control'}
    return result


def raster(path, value):
    from osgeo import gdal, osr
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset = gdal.GetDriverByName('GTiff').Create(str(path), 2, 2, 1, gdal.GDT_Byte)
    dataset.SetGeoTransform((500000, 30, 0, 5000000, 0, -30))
    projection = osr.SpatialReference()
    projection.ImportFromEPSG(32611)
    dataset.SetProjection(projection.ExportToWkt())
    dataset.GetRasterBand(1).SetNoDataValue(0)
    dataset.GetRasterBand(1).Fill(value)
    dataset = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restart-evidence', type=Path, required=True)
    parser.add_argument('--profile-seed-root', action='append', default=[])
    args = parser.parse_args()
    evidence = args.restart_evidence.resolve(strict=True)
    assert os.geteuid() != 0, 'Run through the normal non-root service identity'
    nonce = uuid4().hex[:12]
    batch = Path('/wc1/batch') / ('qa-freshness-archive-' + nonce)
    batch.mkdir()
    root = batch / 'runs/archive'
    root.mkdir(parents=True)
    output = Path(__file__).parent / ('runtime_archive_acceptance_' + nonce + '.json')
    result = {'success': False, 'root': str(root), 'uid': os.geteuid(),
              'gid': os.getegid(), 'groups': os.getgroups(), 'restart_evidence': str(evidence),
              'restart_evidence_sha256': sha(evidence), 'scope': __doc__}

    def flush():
        text = json.dumps(result, indent=2) + '\n'
        output.write_text(text)
        (batch / 'acceptance-manifest.json').write_text(text)

    flush()
    try:
        from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
        from wepppy.nodb.mods.geneva.collaborators._cache_freshness import _Attempt
        from wepppy.nodb.mods.geneva.collaborators.hru_map_geometry_service import GenevaHruMapGeometryService
        from wepppy.nodb.mods.geneva.collaborators.hsg_assignment_service import GenevaHsgAssignmentService
        from wepppy.nodb.project_config_update import project_config_lifecycle_guard
        from wepppy.rq.project_rq_archive import ArchiveRuntime, archive_rq, restore_archive_rq
        import rasterio
        import inspect

        modules = {Path(inspect.getfile(value)).resolve() for value in (
            _Attempt, GenevaHruMapGeometryService, GenevaHsgAssignmentService, archive_rq)}
        result['module_sha256'] = {str(path): sha(path) for path in sorted(modules)}
        result['umask'] = next(line.split(':', 1)[1].strip()
                               for line in Path('/proc/self/status').read_text().splitlines()
                               if line.startswith('Umask:'))
        result['project_device'] = root.stat().st_dev

        owner = SimpleNamespace(wd=str(root), artifact_io=GenevaArtifactIO())
        geneva = owner.artifact_io.root_dir(owner.wd)
        source, bound = root / 'sources/sbs.tif', root / 'sources/bound.tif'
        raster(source, 3)
        raster(bound, 1)
        raster(geneva / 'hru_map.tif', 1)
        (geneva / 'hru_map_legend.json').write_text(json.dumps({'rows': [{'hru_value': 1, 'hru_id': 'one'}]}))
        geometry_service = GenevaHruMapGeometryService()
        geometry = geometry_service.query_feature_collection(owner)
        geometry_path = geneva / 'hru_map_features.wgs.geojson'
        assert geometry['feature_count'] == 1
        alignment = GenevaHsgAssignmentService()._materialize_auto_burn_severity(
            owner, source_path=str(source), bound_tif=str(bound))
        with rasterio.open(alignment) as dataset:
            assert dataset.read(1).tolist() == [[3, 3], [3, 3]]
        prior = sha(geometry_path)
        try:
            with _Attempt(owner, 'hru_map_features.wgs.geojson', 'hru_geometry') as attempt:
                attempt.candidate('failed.geojson').write_text('retained incomplete derivation')
                raise RuntimeError('Intentional disposable retained failure')
        except RuntimeError as exc:
            assert str(exc) == 'Intentional disposable retained failure'
        assert sha(geometry_path) == prior
        assert json.loads((attempt.root / 'status.json').read_text())['status'] == 'failed'
        statuses = [json.loads(path.read_text())['status'] for path in (geneva / 'cache_attempts').glob('*/status.json')]
        assert statuses.count('complete') >= 2 and statuses.count('failed') == 1
        before = inventory(root)
        result['profile_before'] = profiles(args.profile_seed_root)
        result['before'] = before
        result['browse_before'] = asyncio.run(browse_records(root, before))
        messages = []
        runtime = ArchiveRuntime(
            get_current_job=lambda: SimpleNamespace(id='security-runtime-' + nonce),
            get_wd=lambda runid: str(root), get_prep_from_runid=lambda runid: None,
            lock_statuses=lambda runid: {}, clear_nodb_file_cache=lambda runid: [],
            publish_status=lambda channel, message: messages.append(message),
            disk_usage=shutil.disk_usage, zip_file_cls=zipfile.ZipFile,
            project_config_lifecycle_guard=project_config_lifecycle_guard,
            project_config_authority_wd=lambda runid: str(root))
        archive_rq('security-runtime-' + nonce, 'Disposable accepted and failed Geneva artifacts', runtime=runtime)
        archive = next((root / 'archives').glob('*.zip'))
        with zipfile.ZipFile(archive) as saved:
            for relative, record in before.items():
                entry = saved.getinfo(relative + '/' if record['directory'] else relative)
                assert stat.S_IMODE(entry.external_attr >> 16) == record['mode'], relative
                if not record['directory']:
                    assert hashlib.sha256(saved.read(entry)).hexdigest() == record['sha256'], relative
        restore_archive_rq('security-runtime-' + nonce, archive.name, runtime=runtime)
        after = inventory(root)
        assert after == before
        result['after'] = after
        result['browse_after'] = asyncio.run(browse_records(root, after))
        result['profile_after'] = profiles(args.profile_seed_root)
        assert result['profile_after'] == result['profile_before']
        restored_geometry = geometry_service.query_feature_collection(owner)
        assert restored_geometry['feature_collection']['features'] == geometry['feature_collection']['features']
        assert sha(geometry_path) == prior
        assert len(list((geneva / 'cache_attempts').glob('*/status.json'))) == len(statuses)
        assert all(sha(path) == digest for path, digest in result['module_sha256'].items())
        result.update(success=True, archive=str(archive), archive_sha256=sha(archive),
                      project_mode_byte_parity=True, restored_geometry_reused=True,
                      helper_downloads_verified=True, statuses=messages,
                      live_browse_base=f'/weppcloud/batch/{batch.name}/browse/runs/archive/',
                      external_profile_archival='Not performed or implied by project archive')
    except Exception as exc:
        # Evidence boundary: retain the failed operation and re-raise unchanged.
        result['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        flush()
        print(json.dumps({'manifest': str(output), 'project': str(root), 'success': result['success']}))


if __name__ == '__main__':
    main()
