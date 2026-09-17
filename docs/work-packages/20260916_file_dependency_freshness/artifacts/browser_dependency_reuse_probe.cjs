/* Actual maintained controller and real Parquet/DuckDB; transport/UI stubs only. */
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '../../../..');
const {JSDOM} = require(require.resolve('jsdom', {paths:[path.join(root,'wepppy/weppcloud/static-src')]}));
const python = path.join(root, '.venv/bin/python');
const temp = fs.mkdtempSync(path.join(os.tmpdir(),'freshness-browser-'));
const parquet = path.join(temp, 'loss_pw0.hill.parquet');
const observations = [];
function writeParquet(value) {
  execFileSync(python,['-c', 'import sys,pyarrow as pa,pyarrow.parquet as pq; pq.write_table(pa.table({"wepp_id":[1],"Hillslope Area":[1.0],"Runoff Volume":[float(sys.argv[2])*10]}),sys.argv[1])',parquet,String(value)]);
}
function queryParquet(payload) {
  return JSON.parse(execFileSync(python,['-c', 'import sys,json,duckdb; p=json.loads(sys.argv[2]); c=duckdb.connect(); c.from_parquet(sys.argv[1]).create_view("loss"); cur=c.execute("SELECT "+",".join(p["columns"])+" FROM loss ORDER BY wepp_id"); print(json.dumps({"records":[dict(zip([x[0] for x in cur.description],r)) for r in cur.fetchall()]}))',parquet,JSON.stringify(payload)],{encoding:'utf8'}));
}
function fixture() {
  const d = new JSDOM('<form id="build_subcatchments_form"></form>',{url:'https://example.invalid/weppcloud/runs/disposable/cfg/',runScripts:'outside-only'});
  const w = d.window;
  const noop = ()=>{};
  const emitters = [];
  w.WCEvents = {createEmitter() {
    const listeners = {};
    const emitter = {on(k,f){(listeners[k] ||= []).push(f); return noop;}, emit(k,v){(listeners[k]||[]).forEach(f=>f(v));}};
    emitters.push(emitter); return emitter;
  }, useEventMap:(names,e)=>e};
  w.WCForms={serializeForm:()=>({})};
  let queries = 0;
  w.WCHttp={request:async()=>({body:{}}),postJsonWithSessionToken:async()=>({body:{}}),
    postJson:async(url,payload)=>{queries++; return {body:queryParquet(payload)};}};
  w.controlBase=()=>({attach_status_stream:noop,triggerEvent:noop,pushResponseStacktrace:noop});
  w.fromHex=()=>({r:1,g:1,b:1,a:1});
  w.createColormap=()=>({map:()=> '#fff'});
  w.L={layerGroup:()=>({clearLayers:noop,addLayer:noop})};
  w.url_for_run=p=>p;
  w.eval(fs.readFileSync(path.join(root,'wepppy/weppcloud/controllers_js/dom.js'),'utf8'));
  w.eval(fs.readFileSync(path.join(root,'wepppy/weppcloud/controllers_js/subcatchment_delineation.js'),'utf8'));
  return {d,w,sub:w.SubcatchmentDelineation.getInstance(),queries:()=>queries};
}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  writeParquet(25);
  const f=fixture();
  f.sub.renderRunoff(); await settle();
  const before=f.sub.state.dataRunoff['1'].value;
  writeParquet(75);
  f.w.document.dispatchEvent(new f.w.CustomEvent('preflight:update',{detail:{checklist:{wepp:true}}}));
  f.sub.triggerEvent('WEPP_RUN_TASK_COMPLETED',{});
  f.sub.renderRunoff(); await settle();
  const after=f.sub.state.dataRunoff['1'].value;
  const fresh=fixture(); fresh.sub.renderRunoff(); await settle();
  const reload=fresh.sub.state.dataRunoff['1'].value;
  assert.equal(before,25); assert.equal(after,25); assert.equal(reload,75); assert.equal(f.queries(),1);
  observations.push({case:'explicit runoff render after underlying same-path Parquet changes',before,after,reload,
    queries_in_original_controller:f.queries(), real_parquet:true, real_duckdb:true,
    limitation:'DOM, controlBase, and HTTP transport are isolated; no live RQ job or deployed browser exercised. Completion dispatch is diagnostic only; actual Wepp controller sends its own emitter event, to which this controller has no listener.'});
  f.d.window.close(); fresh.d.window.close();
  fs.writeFileSync(path.join(__dirname,'browser_dependency_reuse_probe.json'),JSON.stringify(observations,null,2)+'\n');
  console.log(JSON.stringify(observations,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>fs.rmSync(temp,{recursive:true,force:true}));
