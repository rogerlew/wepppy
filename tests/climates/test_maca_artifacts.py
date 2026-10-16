"""Read MACA values through native CLIGEN, preparation, browse and archive."""
import logging
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd
import pytest
from starlette.testclient import TestClient

from tests.nodb.test_climate_catalog import climate_factory
from tests.rq.test_project_rq_archive import archive_rq_environment
from tests.microservices.test_browse_routes import load_browse, load_run_browse
from wepppy.climates import downscaled_nmme_client as client
from wepppy.climates.cligen import Cligen, CligenStationsManager
from wepppy.climates.edde.cligen import read_cli
from wepppy.nodb.core.climate import Climate, ClimateMode
from wepppy.nodb.core.climate_build_helpers import build_future
from wepppy.nodb.core.wepp_prep_service import WeppPrepService

pytestmark = pytest.mark.integration


def test_selected_source_reaches_native_prepared_and_restored_artifacts(
    monkeypatch, climate_factory, archive_rq_environment, load_run_browse,
):
    climate = climate_factory()
    with climate.locked():
        climate._maca_projection = 'CCSM4/RCP4.5'
    root = Path(climate.wd)
    dates = pd.date_range('2030-01-01', '2030-12-31')
    precip = np.where(np.arange(len(dates)) % 4 == 0, 4., 0.)
    urls = []

    def get(self, url, **kwargs):
        urls.append(url)
        query = parse_qs(urlparse(url).query)
        variable = query['variable-name'][0]
        assert f'_{variable}_CCSM4_r6i1p1_rcp45_2006_2099_' in query['data-path'][0]
        values = precip if variable == 'pr' else np.full(len(dates), {
            'tasmax': 290., 'tasmin': 280., 'rsds': 200., 'uas': 2., 'vas': 1., 'huss': .01,
        }[variable])
        unit = 'mm' if variable == 'pr' else 'K' if variable.startswith('tas') else 'units'
        return SimpleNamespace(status_code=200, json=lambda: {'data': [{
            'yyyy-mm-dd': dates.strftime('%Y-%m-%d').tolist(), f'{variable}({unit})': values.tolist(),
        }]})

    monkeypatch.setattr(client.requests.Session, 'get', get)
    Path(climate.cli_dir).mkdir()
    station = CligenStationsManager().get_station_fromid('wa458928')
    cligen = Cligen(station, wd=climate.cli_dir)
    build_future(cligen, -116, 47, 2030, 2030, climate.cli_dir, 'ws.prn', 'wepp.cli',
                 randseed=1001, model='CCSM4', scenario='rcp45_2006_2099')
    assert len(urls) == 7
    frame = read_cli(root / 'climate/wepp.cli')
    assert frame.index.equals(dates)
    np.testing.assert_allclose(frame.prcp, precip, atol=.15)
    np.testing.assert_allclose(frame.tmax, (round(16.85 * 1.8 + 32) - 32) / 1.8, atol=.05)
    np.testing.assert_allclose(frame.tmin, (round(6.85 * 1.8 + 32) - 32) / 1.8, atol=.05)
    prn = np.loadtxt(root / 'climate/ws.prn')
    np.testing.assert_array_equal(prn[:, 2], 2030)
    np.testing.assert_array_equal(prn[:, 3], np.round(precip / 25.4 * 100))
    np.testing.assert_array_equal(prn[:, 4], round(16.85 * 1.8 + 32))
    np.testing.assert_array_equal(prn[:, 5], round(6.85 * 1.8 + 32))

    (root / 'wepp/runs').mkdir(parents=True)
    # Use the actual preparation copy operation; only unrelated watershed state is synthetic.
    wepp = SimpleNamespace(
        wd=str(root), runs_dir=str(root / 'wepp/runs'), class_name='Wepp', logger=logging.getLogger(__name__),
        climate_instance=SimpleNamespace(climate_mode=ClimateMode.Future, has_climate=True,
                                         sub_summary=lambda top: {'cli_fn': 'wepp.cli'}),
        watershed_instance=SimpleNamespace(sub_n=1, _subs_summary={'11': {}}),
    )
    WeppPrepService().prep_climates(wepp, SimpleNamespace(wepp=lambda top: 1))
    prepared = root / 'wepp/runs/p1.cli'
    assert prepared.read_bytes() == (root / 'climate/wepp.cli').read_bytes()
    pd.testing.assert_frame_equal(read_cli(prepared), frame)

    project, _, _, _ = archive_rq_environment
    monkeypatch.setattr(project, 'get_wd', lambda runid: str(root))
    monkeypatch.setattr('wepppy.nodb.base.redis_nodb_cache_client', None)
    browse = load_run_browse({'demo': root}, SITE_PREFIX='/weppcloud')
    with TestClient(browse.create_app()) as browser:
        (root / 'climate.log').write_text('completed: MACA CCSM4 r6i1p1 rcp45_2006_2099\n')
        expected = {str(path.relative_to(root)): path.read_bytes() for path in (
            root / 'climate.nodb', root / 'climate/ws.prn', root / 'climate/wepp.cli',
            root / 'climate.log', prepared,
        )}
        for relative, content in expected.items():
            response = browser.get(f'/weppcloud/runs/demo/cfg/browse/{relative}?download')
            assert response.status_code == 200
            assert response.content == content
        before = set((root / 'archives').glob('*.zip'))
        project.archive_rq('demo', comment='completed')
        archive = (set((root / 'archives').glob('*.zip')) - before).pop()
        (root / 'climate/wepp.cli').write_text('later partial output')
        project.restore_archive_rq('demo', archive.name)
        for relative, content in expected.items():
            assert (root / relative).read_bytes() == content
        assert Climate.load_detached(str(root)).maca_projection == 'CCSM4/RCP4.5'


def test_replay_validation_failure_retains_working_input_and_real_exception_log(
    monkeypatch, climate_factory, archive_rq_environment, load_run_browse,
):
    from wepppy.nodb.core import climate_build_helpers as helpers
    from wepppy.rq import exception_logging

    climate = climate_factory()
    with climate.locked():
        climate._maca_projection = 'CCSM4/RCP4.5'
    root = Path(climate.wd)
    Path(climate.cli_dir).mkdir()
    source = pd.DataFrame({'pr(mm)': 4., 'tasmax(degc)': 17., 'tasmin(degc)': 7.},
                          index=pd.date_range('2030-01-01', '2030-12-31'))
    monkeypatch.setattr(helpers, 'retrieve_maca_timeseries', lambda *args, **kwargs: source.copy())
    monkeypatch.setattr(exception_logging, 'get_wd', lambda runid: str(root))
    monkeypatch.setattr(exception_logging, 'get_current_job', lambda: None)
    # Actual CLIGEN boundary rejects a replay-incompatible version after PRN writing.
    cligen = Cligen(CligenStationsManager().get_station_fromid('wa458928'), wd=climate.cli_dir, cliver='4.3')
    replay = cligen.run_observed
    browse = load_run_browse({'demo': root}, SITE_PREFIX='/weppcloud')
    with TestClient(browse.create_app()) as browser:
        def observe_working(*args, **kwargs):
            response = browser.get('/weppcloud/runs/demo/cfg/browse/climate/ws.prn?download')
            assert response.status_code == 200
            assert response.content == (root / 'climate/ws.prn').read_bytes()
            assert not (root / 'climate/wepp.cli').exists()
            return replay(*args, **kwargs)
        monkeypatch.setattr(cligen, 'run_observed', observe_working)

        @exception_logging.with_exception_logging
        def failed_build(runid):
            helpers.build_future(cligen, -116, 47, 2030, 2030, climate.cli_dir, 'ws.prn', 'wepp.cli',
                                 model='CCSM4', scenario='rcp45_2006_2099')

        with pytest.raises(NotImplementedError, match='version must be greater than 5'):
            failed_build('demo')
        diagnostic = (root / 'exceptions.log').read_text()
        assert 'failed_build failed' in diagnostic and 'NotImplementedError' in diagnostic
        assert not (root / 'climate/wepp.cli').exists()
        expected = {name: (root / name).read_bytes() for name in ('climate.nodb', 'climate/ws.prn', 'exceptions.log')}
        for name, content in expected.items():
            response = browser.get(f'/weppcloud/runs/demo/cfg/browse/{name}?download')
            assert response.status_code == 200 and response.content == content

    project, _, _, _ = archive_rq_environment
    monkeypatch.setattr(project, 'get_wd', lambda runid: str(root))
    project.archive_rq('demo', comment='actual failed native build')
    archive = next((root / 'archives').glob('*.zip'))
    (root / 'climate/ws.prn').write_text('later partial overwrite')
    project.restore_archive_rq('demo', archive.name)
    for name, content in expected.items():
        assert (root / name).read_bytes() == content
    monkeypatch.setattr('wepppy.nodb.base.redis_nodb_cache_client', None)
    assert Climate.load_detached(str(root)).maca_projection == 'CCSM4/RCP4.5'
