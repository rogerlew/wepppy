"""Exercise real Redis/NoDb preference and worker/publication contention."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
import json
import os
import time
import uuid
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.postfire_debris_flow import production as p
from wepppy.nodb.mods.postfire_debris_flow.postfire_debris_flow import PostfireDebrisFlow
from wepppy.nodb.mods.postfire_debris_flow.publication import publish_outputs

runid = 'model-wiring-check-' + uuid.uuid4().hex[:8]
wd = Path('/wc1/runs/mo')/runid
wd.mkdir(parents=True)
ron = Ron(str(wd), 'disturbed9002_wbt.cfg')
controller = PostfireDebrisFlow(str(wd), ron.config_stem)
identity = uuid.uuid4().hex
attempt = {'id':identity,'model':'M1','job_id':'contention-check','phase':'queued',
           'created_at':p.now(),'retryable':False,'snapshot':{'frequency':'cli'}}
controller.change(lambda state: state.update(run_attempt=attempt))

for operation in ('phase', 'publication'):
    controller = PostfireDebrisFlow.getInstance(str(wd))
    if operation == 'publication':
        results = p.directory(wd,identity)/'results'
        results.mkdir()
        for name in p.FILES: (results/name).write_text('retained contention fixture: '+name)
        accepted = {'id':identity,'model':'M1','completed_at':p.now(),'snapshot':{},
                    'artifacts':{str(f.relative_to(wd)):p.signature(wd,f,strong=True) for f in results.iterdir()}}
        # Arrange accepted fixture without invoking publication before contention.
        with controller.locked(): controller._state['last_successful_run'] = accepted
    entered, release = Event(), Event()
    def select(state):
        state['model'] = 'M3'
        entered.set()
        assert release.wait(5)
    def work():
        if operation == 'phase': p.update_attempt(wd, 'run_attempt', identity, phase='running')
        else: publish_outputs(wd)
    with ThreadPoolExecutor(2) as pool:
        selection = pool.submit(controller.change, select)
        assert entered.wait(5)
        worker = pool.submit(work)
        time.sleep(.25)
        assert not worker.done(), 'worker failed or bypassed the held preference lock'
        release.set()
        selection.result(timeout=10)
        worker.result(timeout=10)
    saved = PostfireDebrisFlow.load_detached(str(wd)).state
    assert saved['model'] == 'M3' and saved['run_attempt']['phase'] == 'running'
    if operation == 'publication':
        for name in p.FILES:
            assert (wd/'postfire_debris_flow'/name).read_bytes() == (results/name).read_bytes()
    print('PASS',operation,'waited for selection then preserved both state changes')
print(json.dumps({'runid':runid,'uid':os.getuid(),'gid':os.getgid(),'path':str(wd)}))
