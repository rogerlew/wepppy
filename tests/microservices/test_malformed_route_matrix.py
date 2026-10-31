"""Every route in the repaired shared/default families traverses its real wrapper."""
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.microservice

MODULES = ('rhem','wepp','bootstrap','climate','landuse','soils','treatments','ash',
           'watershed','dss_export','swat','openet_ts','rap_ts','polaris','rusle',
           'debris_flow','geneva','omni','run_sync','migration','roads','debug',
           'fork_archive','ag_fields','export','batch','culvert','upload_climate',
           'upload_disturbed','upload_huc_fire','upload_batch_runner',
           'landuse_soils','project','builder','project_config_update')


def cases():
    result=[]
    for name in MODULES:
        module=importlib.import_module('wepppy.microservices.rq_engine.'+name+'_routes')
        for route in module.router.routes:
            if 'POST' in route.methods:
                result.append(pytest.param(name, route.path, id=name+':'+route.path.rsplit('/',1)[-1]))
    return result


@pytest.mark.parametrize('name,path', cases())
def test_malformed_body_cannot_reach_controller_or_queue(name,path,monkeypatch,tmp_path):
    module=importlib.import_module('wepppy.microservices.rq_engine.'+name+'_routes')
    claims={'sub':'1','token_class':'user','roles':['Admin','Root'],'scope':'rq:enqueue rq:export bootstrap:enable bootstrap:token:mint bootstrap:checkout'}
    for field in ('require_jwt','authorize_run_access','require_roles','require_token_class','require_feature_access'):
        if hasattr(module,field):monkeypatch.setattr(module,field,lambda *a,**k:claims)
    if hasattr(module,'get_wd'):monkeypatch.setattr(module,'get_wd',lambda *a,**k:str(tmp_path))
    # Config/access checks retain precedence, but do not need a real project for
    # this malformed-transport test. Persistence evidence lives in companion tests.
    for field in ('_config_mismatch_response','_watershed_abstraction_state_response','_active_job_conflict_response','_ensure_anonymous_access'):
        if hasattr(module,field):monkeypatch.setattr(module,field,lambda *a,**k:None)
    for dirname in ('landuse','soils','watershed','ash','climate','omni','wepp'):
        (tmp_path/dirname).mkdir()
    if hasattr(module, '_batch_runner_feature_enabled'):
        monkeypatch.setattr(module, '_batch_runner_feature_enabled', lambda: True)
    effects=[]
    def forbidden(*a,**k):
        effects.append('business boundary')
        raise AssertionError('malformed input reached controller/queue')
    for key in ('Ron','Wepp','Watershed','Soils','Landuse','Rhem','Geneva','Omni','Swat','Ash','Treatments','AgFields','RedisPrep'):
        obj=getattr(module,key,None)
        if obj is not None and hasattr(obj,'getInstance'):monkeypatch.setattr(obj,'getInstance',forbidden)
    if hasattr(module,'enqueue_tracked_rq_job'):monkeypatch.setattr(module,'enqueue_tracked_rq_job',forbidden)
    app=FastAPI();app.include_router(module.router,prefix='/api')
    concrete=path.replace('{runid}','test-run').replace('{config}','cfg')
    for field in ('task','task_name','job_id','name','key','field_id','batch_name','batch_uuid'):
        concrete=concrete.replace('{'+field+'}','test')
    with TestClient(app,raise_server_exceptions=False) as client:
        response=client.post('/api'+concrete,content='{',headers={'Content-Type':'application/json'})
    assert response.status_code==400, response.text
    expected_code = 'invalid_rows_payload' if path.endswith('/landuse-map/save') else 'invalid_request'
    if (name == 'export' and path.endswith(('/features', '/resolve'))) or path.endswith('/rotation-mapping'):
        expected_code = 'validation_error'  # Existing strict features-export schema contract.
    if name in ('builder', 'project_config_update'):
        expected_code = 'validation_error'
    assert response.json()['error']['code']==expected_code,response.text
    assert effects==[]
