"""Real revised/failed climate diagnostics through canonical browse and ZIP restore."""
from pathlib import Path
import zipfile

import pytest

from tests.climates.test_prism_temperature_ordering import write_source, normals
from tests.rq.test_project_rq_archive import archive_rq_environment
from tests.microservices.test_browse_routes import load_browse, load_run_browse, TestClient
from wepppy.climates.edde.cligen import revise_prism
from wepppy.climates.edde.client import DataQualityError

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('failed', [False, True])
def test_revision_records_browse_archive_restore(archive_rq_environment, load_run_browse, failed):
    project, tmp_path, _, _ = archive_rq_environment
    root = tmp_path / 'demo'
    attempt = root / 'climate/prism-build-fixture'
    attempt.mkdir(parents=True)
    source = write_source(attempt / 'source.cli', bad='nan' if failed else None)
    output = attempt / 'revised.cli'
    if failed:
        with pytest.raises(DataQualityError): revise_prism(source, output, normals(), normals(True))
    else:
        revise_prism(source, output, normals(), normals(True))
    log = Path(str(output) + '.temperature-ordering.log')
    assert ('status=complete' in log.read_text()) is not failed
    expected = {str(p.relative_to(root)): p.read_bytes() for p in attempt.iterdir() if p.is_file()}
    browse = load_run_browse({'demo': root}, SITE_PREFIX='/weppcloud')
    with TestClient(browse.create_app()) as client:
        listing = client.get('/weppcloud/runs/demo/cfg/browse/climate/prism-build-fixture/')
        assert listing.status_code == 200 and log.name in listing.text
        for relative, contents in expected.items():
            response = client.get(f'/weppcloud/runs/demo/cfg/browse/{relative}?download')
            assert response.status_code == 200 and response.content == contents
    project.archive_rq('demo', comment='PRISM repair diagnostics')
    archive, = (root / 'archives').glob('*.zip')
    with zipfile.ZipFile(archive) as zipped:
        for relative, contents in expected.items(): assert zipped.read(relative) == contents
    log.write_text('later mutation')
    project.restore_archive_rq('demo', archive.name)
    for relative, contents in expected.items(): assert (root / relative).read_bytes() == contents
