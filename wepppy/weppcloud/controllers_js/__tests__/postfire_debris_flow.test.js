/** @jest-environment jsdom */
const createControlBaseStub = require('./helpers/control_base_stub');
describe('PostfireDebrisFlow', () => {
    let instance;
    beforeEach(async () => {
        jest.resetModules();
        window.preflightConnected = true;
        document.body.innerHTML = `<form id="postfire_debris_flow_form"><div data-pfdf-required></div><p data-pfdf-candidate></p><div data-pfdf-summary></div><p data-pfdf-message></p><p data-pfdf-warning></p><div data-pfdf-files></div><input name="file" type="file"><input name="companion" type="file"><select name="scale_mode"><option value="auto">Auto</option><option value="custom">Custom</option></select><div data-pfdf-custom></div><div data-pfdf-companion></div><input type="radio" name="frequency_source" value="cli" checked><input type="radio" name="frequency_source" value="noaa"><p data-pfdf-noaa></p><button data-pfdf-action="upload"></button><button data-pfdf-action="run"></button></form>`;
        await import('../dom.js'); await import('../events.js');
        window.WCHttp = {requestWithSessionToken: jest.fn().mockResolvedValue({body: {result: {}}})};
        global.url_for_run = (path) => path;
        const base = createControlBaseStub().base;
        global.controlBase = () => base;
        await import('../postfire_debris_flow.js');
        instance = window.PostfireDebrisFlow.getInstance();
    });
    afterEach(() => { instance.destroy(); delete window.PostfireDebrisFlow; });
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
        expect(document.querySelector('[data-pfdf-candidate]').textContent).toContain('replacement.tif');
        expect(document.querySelector('[data-pfdf-summary]').textContent).toContain('accepted.tif');
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
