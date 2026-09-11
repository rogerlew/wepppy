/** @jest-environment jsdom */
const createControlBaseStub = require('./helpers/control_base_stub');
describe('PostfireDebrisFlow', () => {
    let instance, realBase;
    beforeEach(async () => {
        jest.resetModules();
        window.preflightConnected = true;
        document.body.innerHTML = `<form id="postfire_debris_flow_form"><div data-pfdf-required></div><div data-pfdf-candidate-field hidden><div class="wc-field wc-field--display"><span class="wc-field__label">Uploaded dNBR map</span><div class="wc-text-display"><code data-pfdf-candidate></code></div></div></div><div data-pfdf-summary></div><p data-job-hint></p><div id="postfire_status_panel"><div id="status"></div><div id="rq_job"></div></div><details id="postfire_stacktrace_panel"><div id="stacktrace"></div></details><p data-pfdf-message></p><p data-pfdf-warning></p><div data-pfdf-files></div><input name="file" type="file"><input name="companion" type="file"><select name="scale_mode"><option value="auto">Auto</option><option value="custom">Custom</option></select><div data-pfdf-custom></div><div data-pfdf-companion></div><input type="radio" name="frequency_source" value="cli" checked><input type="radio" name="frequency_source" value="noaa"><p data-pfdf-noaa></p><button data-pfdf-action="upload"></button><button data-pfdf-action="run"></button></form>`;
        await import('../dom.js'); await import('../events.js');
        window.WCHttp = {requestWithSessionToken: jest.fn().mockResolvedValue({body: {result: {}}})};
        global.url_for_run = (path) => path;
        const base = createControlBaseStub().base;
        realBase = global.controlBase();
        global.controlBase = () => base;
        await import('../postfire_debris_flow.js');
        instance = window.PostfireDebrisFlow.getInstance();
    });
    afterEach(() => { instance.destroy(); delete window.PostfireDebrisFlow; });
    test('remount binds readiness to the replacement form', async () => {
        const old = document.querySelector('form');
        const replacement = old.cloneNode(true);
        old.replaceWith(replacement);
        const destroy = jest.spyOn(instance, 'destroy');
        instance = window.PostfireDebrisFlow.remount();
        expect(destroy).toHaveBeenCalledTimes(1);
        window.WCHttp.requestWithSessionToken.mockResolvedValue({body:{result:{required:[{key:'k',ready:false,message:'Prepare in RUSLE'}],frequency_source:'cli'}}});
        await instance.refresh();
        expect(replacement.querySelector('[data-pfdf-required]').textContent).toContain('Prepare in RUSLE');
        expect(old.querySelector('[data-pfdf-required]').textContent).toBe('');
    });
    test('summary is escaped, persists and NOAA is disabled', () => {
        instance.render({required: [{key:'k',ready:false,message:'Prepare in RUSLE',control:'#rusle'}],noaa_available:false,frequency_source:'cli',upload_ready:true,run_ready:false,
            dnbr:{filename:'<img src=x>',format:'GTiff',dtype:'int16',cell_size_m:[10,10],coverage_fraction:.94,source_range:[-120,850],prepared_range:[-.12,.85],scale_mode:'auto',scale_method:'distribution',scale_factor:.001,add_offset:0}});
        expect(document.querySelector('[data-pfdf-summary]').textContent).toContain('<img src=x>');
        expect(document.querySelector('[data-pfdf-summary] img')).toBeNull();
        expect(document.querySelector('[data-pfdf-summary] table')).not.toBeNull();
        expect(document.querySelector('[value="noaa"]').disabled).toBe(true);
        expect(document.querySelector('[data-pfdf-action="run"]').disabled).toBe(true);
    });
    test('preflight refreshes state and disconnection disables run', async () => {
        document.dispatchEvent(new CustomEvent('preflight:connection',{detail:{connected:false}}));
        expect(document.querySelector('[data-pfdf-action="run"]').disabled).toBe(true);
        await instance.refresh();
        expect(window.WCHttp.requestWithSessionToken).toHaveBeenCalledWith(expect.stringContaining('/state'),expect.any(Object));
    });
    test('state-fetch failure disables cached readiness and empty upload', async () => {
        const ready={eligible:true,readonly:false,required:[{key:'dnbr',ready:true}],noaa_available:false,frequency_source:'cli',upload_ready:true,run_ready:true};
        window.WCHttp.requestWithSessionToken.mockResolvedValue({body:{result:ready}});
        await instance.refresh();
        expect(document.querySelector('[data-pfdf-action="run"]').disabled).toBe(false);
        expect(document.querySelector('[data-pfdf-action="upload"]').disabled).toBe(true);
        window.WCHttp.requestWithSessionToken.mockRejectedValue(new Error('service unavailable'));
        await instance.refresh();
        expect(document.querySelector('[data-pfdf-action="run"]').disabled).toBe(true);
        expect(document.querySelector('[data-pfdf-message]').textContent).toContain('Could not update');
    });
    test('failed candidate is named while accepted summary persists', () => {
        instance.render({required:[],frequency_source:'cli',upload_ready:true,upload:{id:'candidate',filename:'replacement.tif',phase:'needs_scale',retryable:true,error:{message:'Choose a scale.'}},
            dnbr:{id:'accepted',filename:'accepted.tif',format:'GTiff',dtype:'int16',cell_size_m:[10,10],coverage_fraction:1,source_range:[0,900],prepared_range:[0,.9],scale_mode:'auto',scale_method:'distribution',scale_factor:.001,add_offset:0}});
        expect(document.querySelector('[data-pfdf-candidate-field]').hidden).toBe(false);
        expect(document.querySelector('code[data-pfdf-candidate]').textContent).toBe('replacement.tif');
        expect(document.querySelector('[data-pfdf-summary]').textContent).toContain('accepted.tif');
    });

    test('reload reattaches the latest failed job once and preserves its message', async () => {
        const failed = {frequency_source:'cli', required:[], upload:{phase:'failed',
            job_id:'0d4bc387-010e-44f7-8d3b-ef5f20691021',created_at:'2026-09-11T01:23:31Z',
            error:{message:'The operation could not finish.'}},
            run:{phase:'complete',job_id:'older',created_at:'2026-09-10T00:00:00Z'}};
        window.WCHttp.requestWithSessionToken.mockResolvedValue({body:{result:failed}});
        await instance.refresh();
        await instance.refresh();
        expect(instance.set_rq_job_id).toHaveBeenCalledTimes(1);
        expect(instance.set_rq_job_id).toHaveBeenCalledWith(instance, failed.upload.job_id);
        expect(document.querySelector('[data-pfdf-message]').textContent).toBe(failed.upload.error.message);
    });

    test('standard job HTML keeps links and separated timestamps, and escapes tracebacks', () => {
        instance.rq_job_id = '0d4bc387-010e-44f7-8d3b-ef5f20691021';
        instance.rq_job_status = {status:'failed',started_at:'2026-09-11T01:23:33Z',ended_at:'2026-09-11T01:23:39Z'};
        realBase.render_job_status(instance);
        realBase.render_job_hint(instance);
        expect(document.querySelector('[data-job-hint] a').textContent).toBe(instance.rq_job_id);
        expect(document.querySelector('#rq_job > div').textContent).toBe('Status: Failed');
        expect(document.querySelectorAll('#rq_job > div')[1].textContent).toContain('Started:');
        expect(document.querySelectorAll('#rq_job span')).toHaveLength(2);
        realBase.pushResponseStacktrace(instance,{error:{message:'Failure <script>bad()</script>',details:['Trace <img src=x onerror=bad()>']}});
        expect(document.querySelector('#stacktrace').textContent).toContain('<script>');
        expect(document.querySelector('#stacktrace script, #stacktrace img')).toBeNull();
        instance.render({frequency_source:'cli',required:[],upload:{phase:'failed',error:{message:'Correct the map.'}}});
        expect(document.querySelector('[data-job-hint] a').textContent).toBe(instance.rq_job_id);
    });

    test('retry clears old Details before posting without losing the accepted map or job link', async () => {
        instance.reset_panel_state=realBase.reset_panel_state;
        instance.rq_job_id='old-job';
        realBase.render_job_hint(instance);
        document.querySelector('#stacktrace').textContent='old failure';
        window.WCHttp.requestWithSessionToken.mockResolvedValue({body:{result:{frequency_source:'cli',required:[],upload_ready:true,upload:{id:'candidate',phase:'failed',retryable:true,filename:'map.tif'}}}});
        await instance.refresh();
        window.WCHttp.postJsonWithSessionToken=jest.fn().mockImplementation(()=>{
            expect(document.querySelector('#stacktrace').textContent).toBe('');
            expect(document.querySelector('[data-pfdf-message]').textContent).toBe('Uploading dNBR…');
            expect(document.querySelector('[data-job-hint] a').textContent).toBe('old-job');
            return Promise.resolve({body:{job_id:'new-job'}});
        });
        document.querySelector('[data-pfdf-action="upload"]').click();
        await new Promise(resolve=>setTimeout(resolve,0));
        expect(window.WCHttp.postJsonWithSessionToken).toHaveBeenCalledTimes(1);
    });

    test('out-of-study area warning is inline and nonblocking', async () => {
        const state={eligible:true,required:[{key:'dnbr',ready:true}],frequency_source:'cli',upload_ready:true,
            results:{current:true,area_warning:true,files:[],completed_at:'2026-09-10T00:00:00Z'}};
        window.WCHttp.requestWithSessionToken.mockResolvedValue({body:{result:state}});
        await instance.refresh();
        expect(document.querySelector('[data-pfdf-warning]').textContent).toContain('outside the study basin size range');
        expect(document.querySelector('[data-pfdf-action="run"]').disabled).toBe(false);
    });

});
