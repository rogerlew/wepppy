(function (global) {
    'use strict';
    var singleton;
    function create() {
        var dom = global.WCDom, http = global.WCHttp;
        var form = dom.qs('#postfire_debris_flow_form');
        var controller = controlBase();
        var state = null, timer = null, requestNumber = 0, connected = global.preflightConnected === true, sourceEdited = false;
        var submitting = false, live = false;
        function field(name) { return form.querySelector('[name="' + name + '"]'); }
        function node(role) { return form.querySelector('[data-pfdf-' + role + ']'); }
        function url(action) { return url_for_run('postfire-debris-flow/' + action, {prefix: '/rq-engine/api'}); }
        function message(text) { node('message').textContent = text; }
        function adapter(element) {
            return {length: element ? 1 : 0, element: element,
                text: function (value) { if (element) { element.textContent = value; } },
                // controlBase supplies escaped markup for job links, status and tracebacks.
                html: function (value) { if (element) { element.innerHTML = value == null ? '' : String(value); } },
                append: function (value) { if (element && value != null) { if (value instanceof global.Node) { element.append(value); } else { element.insertAdjacentHTML('beforeend',String(value)); } } },
                empty: function () { if (element) { element.textContent = ''; } },
                show: function () { if (element) { element.hidden = false; } },
                hide: function () { if (element) { element.hidden = true; } }};
        }
        controller.form = form;
        controller.events = global.WCEvents.createEmitter();
        controller.status = adapter(form.querySelector('#status'));
        controller.stacktrace = adapter(form.querySelector('#stacktrace'));
        controller.rq_job = adapter(form.querySelector('#rq_job'));
        controller.hint = adapter(form.querySelector('[data-job-hint]'));
        controller.statusPanelEl = dom.qs('#postfire_status_panel');
        controller.stacktracePanelEl = dom.qs('#postfire_stacktrace_panel');
        controller.poll_completion_event = 'POSTFIRE_TASK_COMPLETED';
        controller.attach_status_stream(controller, {element: dom.qs('#postfire_status_panel'), channel: 'postfire_debris_flow', runId: global.runid, logLimit:200});
        function table(rows) {
            var result = document.createElement('table');
            result.className = 'wc-table';
            rows.forEach(function (row) {
                var tr = document.createElement('tr'), th = document.createElement('th'), td = document.createElement('td');
                th.scope = 'row'; th.textContent = row[0];
                if (row[1] instanceof global.Node) { td.append(row[1]); } else { td.textContent = row[1]; }
                tr.append(th,td); result.append(tr);
            });
            return result;
        }
        function dimensional(value, unit) {
            unit = unit || "m";
            var span = document.createElement('span');
            if (global.UnitizerClient && global.UnitizerClient.getClientSync()) {
                span.innerHTML = global.UnitizerClient.renderValue(Number(value),unit,{includeUnits:true});
            } else { span.textContent = value + ' ' + unit; }
            return span;
        }
        function render(next) {
            state = next;
            var rows = (next.required || []).filter(function (item) { return item.key !== 'dnbr'; }).map(function (item) {
                var labels = {watershed:'Watershed',soils:'Soils',sbs:'Soil burn severity',k:'Soil erodibility (K)',climate:'Climate'};
                var value = 'Ready';
                if (!item.ready) { value = document.createElement('a'); value.href = item.control; value.textContent = item.message; }
                return [labels[item.key],value];
            });
            node('required').replaceChildren(table(rows));
            field('frequency_source').disabled = !!next.readonly;
            var noaa = form.querySelector('[name="frequency_source"][value="noaa"]');
            noaa.disabled = !!next.readonly || !next.noaa_available;
            node('noaa').hidden = !!next.noaa_available;
            if (!sourceEdited) {
                form.querySelectorAll('[name="frequency_source"]').forEach(function (radio) { radio.checked = radio.value === next.frequency_source; });
            }
            var uploadBusy = next.upload && ['staged','queued','running','enqueue_unknown'].indexOf(next.upload.phase) >= 0;
            var runBusy = next.run && ['staged','queued','running','enqueue_unknown'].indexOf(next.run.phase) >= 0;
            var candidate = next.upload && next.upload.retryable ? next.upload : next.dnbr;
            var hasFile = !!field('file').files[0];
            form.querySelector('[data-pfdf-action="upload"]').disabled = submitting || !live || !next.upload_ready || uploadBusy || !(hasFile || candidate);
            node('candidate-field').hidden = hasFile || !candidate;
            node('candidate').textContent = !hasFile && candidate ? candidate.filename : '';
            var selectedSource = form.querySelector('[name="frequency_source"]:checked');
            var ready = !!next.eligible && !next.readonly && (next.required || []).every(function (item) {return item.ready;}) && (selectedSource && (selectedSource.value !== 'noaa' || next.noaa_available));
            form.querySelector('[data-pfdf-action="run"]').disabled = submitting || !live || !connected || !ready || runBusy || uploadBusy;
            var d = next.dnbr;
            if (d) {
                var size = document.createElement('span'); size.append(dimensional(d.cell_size_m[0]),' × ',dimensional(d.cell_size_m[1]));
                var scale = d.scale_factor === .001 && !d.add_offset ? 'Divide by 1,000' : 'Multiply by ' + d.scale_factor + (d.add_offset ? '; add ' + d.add_offset : '');
                scale += d.scale_mode === 'auto' ? ' (Auto — ' + (d.scale_method === 'distribution' ? 'value distribution' : 'map metadata') + ')' : ' (selected)';
                node('summary').replaceChildren(table([ ['File',d.filename],['Format / data type',d.format + ' / ' + d.dtype],['Prepared cell size',size],['Watershed coverage',(100*d.coverage_fraction).toFixed(1)+'%'],['Uploaded values',d.source_range.map(function (v) {return Number(v.toPrecision(4));}).join(' to ')],['Applied scale',scale],['Prepared dNBR values',d.prepared_range.map(function (v) {return Number(v.toPrecision(4));}).join(' to ')]]));
            } else { node('summary').replaceChildren(); }
            var active = uploadBusy ? next.upload : runBusy ? next.run : null;
            var latest = [next.upload, next.run].filter(Boolean).sort(function (a,b) { return String(b.created_at || '').localeCompare(String(a.created_at || '')); })[0];
            var tracked = active || latest;
            if (tracked && tracked.job_id && controller._trackedJob !== tracked.job_id) {
                controller._trackedJob = tracked.job_id;
                controller.set_rq_job_id(controller,tracked.job_id);
            }
            if (submitting) { message(submitting === 'run' ? 'Waiting to run…' : 'Uploading dNBR…'); }
            else if (active) {
                message(uploadBusy ? 'Preparing dNBR…' : 'Calculating debris-flow likelihood…');
            } else if (latest && latest.error) { message(latest.error.message); }
            else if (next.freshness === 'stale') { message('Inputs changed. Run the model again.'); }
            else if (next.results) { message(next.results.partial ? 'Run complete. Some probabilities could not be calculated.' : 'Run complete.'); }
            else if (d && d.coverage_fraction < 1) { message('The dNBR map covers only part of the watershed. Calculations will use the available dNBR values.'); }
            else { message((next.required || []).filter(function (item) {return !item.ready;}).map(function (item) {return item.message;}).join('. ')); }
            node('warning').replaceChildren();
            if (next.results && next.results.area_warning) {
                node('warning').append(next.results.current ? 'This watershed is outside the study basin size range (' : 'Previous run: watershed outside the study basin size range (', dimensional(.2,'km^2'),'–',dimensional(8,'km^2'),'). Interpret these likelihood estimates with caution.');
            }
            node('files').replaceChildren();
            if (next.results) {
                var title = document.createElement('p'); title.textContent = (next.results.current ? 'Download model files' : 'Previous run') + ' — ' + new Date(next.results.completed_at).toLocaleString();
                node('files').append(title);
                next.results.files.forEach(function (file) { var link=document.createElement('a'); link.href=file.url; link.dataset.pfdfDownload=file.name; link.textContent=file.name; node('files').append(link,document.createTextNode(' ')); });
            }
        }
        function refresh() {
            var number = ++requestNumber;
            return http.requestWithSessionToken(url('state'),{method:'GET'}).then(function (response) {
                if (number === requestNumber) { live = true; render(response.body.result); }
            }).catch(function () { if (number === requestNumber) { live = false; if(state) {render(state);} message('Could not update project readiness. Reload to try again.'); } });
        }
        function preflight() { global.clearTimeout(timer); timer=global.setTimeout(refresh,150); }
        function connection(event) {
            connected=!!event.detail.connected;
            if (connected) { preflight(); } else { form.querySelector('[data-pfdf-action="run"]').disabled=true; if (state) { render(state); } }
        }
        function selection() {
            node('custom').hidden=field('scale_mode').value!=='custom';
            node('companion').hidden=!(field('file').files[0] && /\.vrt$/i.test(field('file').files[0].name));
        }
        async function submit(action) {
            if (submitting || !state || state.readonly) { return; }
            controller.reset_panel_state(controller, {clearSummary:false});
            submitting=action; render(state);
            var failure = null;
            try {
                var result, payload;
                if (action==='run') {
                    payload={frequency_source:form.querySelector('[name="frequency_source"]:checked').value};
                    result=await http.postJsonWithSessionToken(url('run-m1'),payload,{form:form}); sourceEdited=false;
                } else {
                    payload={scale_mode:field('scale_mode').value};
                    if (payload.scale_mode==='custom') { payload.scale_factor=Number(field('scale_factor').value);payload.add_offset=Number(field('add_offset').value); }
                    var file=field('file').files[0];
                    if (file) {
                        var body=new FormData(); Object.keys(payload).forEach(function (key) {body.append(key,payload[key]);});body.append('file',file);
                        if (/\.vrt$/i.test(file.name) && field('companion').files[0]) {body.append('companion',field('companion').files[0]);}
                        result=await http.requestWithSessionToken(url('upload-dnbr'),{method:'POST',body:body,form:form});
                        field('file').value='';field('companion').value='';
                    } else {
                        payload.candidate_id=state.upload && state.upload.retryable ? state.upload.id : state.dnbr && state.dnbr.id;
                        if (!payload.candidate_id) { throw new Error('Choose a dNBR raster file.'); }
                        result=await http.postJsonWithSessionToken(url('retry-dnbr'),payload,{form:form});
                    }
                }
                controller._trackedJob = result.body.job_id;
                controller.set_rq_job_id(controller,result.body.job_id);
                await refresh();
            } catch (error) { failure=error.message || 'The operation could not finish.'; }
            finally {submitting=false; if(state) {render(state);} if(failure) {message(failure);}}
        }
        dom.delegate(form,'click','[data-pfdf-download]',async function (event) {
            event.preventDefault();
            try {
                var response=await http.requestWithSessionToken(this.href,{method:'GET'});
                var blobUrl=global.URL.createObjectURL(response.body);
                var anchor=document.createElement('a');anchor.href=blobUrl;anchor.download=this.dataset.pfdfDownload;anchor.click();
                global.setTimeout(function () {global.URL.revokeObjectURL(blobUrl);},1000);
            } catch (error) {message('Could not download model files.');}
        });
        dom.delegate(form,'click','[data-pfdf-action]',function (event) {event.preventDefault();submit(this.dataset.pfdfAction);});
        form.addEventListener('change',function(event) {selection();if(event.target.name==='frequency_source') {sourceEdited=true;} if(state) {render(state);}});
        function unitChange() { if(state) {render(state);} }
        document.addEventListener('unitizer:preferences-changed',unitChange);
        document.addEventListener('preflight:update',preflight);
        document.addEventListener('preflight:connection',connection);
        controller.events.on('job:completed',preflight); controller.events.on('job:error',preflight);
        controller.bootstrap=function () {selection();refresh();if(global.UnitizerClient) {global.UnitizerClient.ready().then(function () {if(state) {render(state);}});}};
        controller.refresh=refresh;controller.render=render;
        controller.destroy=function () {requestNumber++;controller.stop_job_status_polling(controller);controller.detach_status_stream(controller);document.removeEventListener('unitizer:preferences-changed',unitChange);global.clearTimeout(timer);document.removeEventListener('preflight:update',preflight);document.removeEventListener('preflight:connection',connection);};
        return controller;
    }
    global.PostfireDebrisFlow={
        getInstance:function () {if(!singleton) {singleton=create();}return singleton;},
        remount:function () {if(singleton) {singleton.destroy();}singleton=create();return singleton;}
    };
}(window));
