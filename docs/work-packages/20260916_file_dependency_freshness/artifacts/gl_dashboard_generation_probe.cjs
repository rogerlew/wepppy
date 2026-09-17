/* Actual maintained ES module, real Parquet + DuckDB, isolated query transport. */
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'../../../..');
const python=path.join(root,'.venv/bin/python');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'freshness-gl-'));
const parquet=path.join(temp,'loss_pw0.all_years.hill.parquet');
function write(value){execFileSync(python,['-c',
  'import sys,pyarrow as pa,pyarrow.parquet as pq; v=float(sys.argv[2]); d={"wepp_id":[1,1],"topaz_id":[11,11],"year":[2000,2001]}; d.update({k:[v,v+1] for k in ["Runoff Volume","Subrunoff Volume","Baseflow Volume","Soil Loss","Sediment Deposition","Sediment Yield"]}); pq.write_table(pa.table(d),sys.argv[1])',parquet,String(value)]);}
function query(payload){return JSON.parse(execFileSync(python,['-c',
  'import sys,json,duckdb; p=json.loads(sys.argv[2]); c=duckdb.connect(); c.from_parquet(sys.argv[1]).create_view("loss"); c.execute("CREATE VIEW hill AS SELECT DISTINCT wepp_id,topaz_id FROM loss"); sql="SELECT "+",".join(p["columns"])+" FROM loss INNER JOIN hill USING (wepp_id) WHERE loss.year="+str(int(p["filters"][0]["value"])); cur=c.execute(sql); print(json.dumps({"records":[dict(zip([x[0] for x in cur.description],r)) for r in cur.fetchall()]}))',parquet,JSON.stringify(payload)],{encoding:'utf8'}));}
(async()=>{
  const source=fs.readFileSync(path.join(root,'wepppy/weppcloud/static/js/gl-dashboard/data/wepp-data.js'),'utf8');
  const {createWeppDataManager}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
  function manager(){const state={baseWeppYearlyCache:{}};let requests=0;return {state,requests:()=>requests,
    reader:createWeppDataManager({ctx:{runid:'disposable',config:'cfg'},getState:()=>state,
      setValue:(k,v)=>{state[k]=v;},setState:v=>Object.assign(state,v),
      postBaseQueryEngine:async payload=>{requests++;return query(payload);},WEPP_YEARLY_PATH:'wepp/output/interchange/loss_pw0.all_years.hill.parquet'})};}
  write(25); const first=manager();
  const original=(await first.reader.loadBaseWeppYearlyData(2000))['11'].runoff_volume;
  write(75);
  const cached=(await first.reader.loadBaseWeppYearlyData(2000))['11'].runoff_volume;
  const newYear=(await first.reader.loadBaseWeppYearlyData(2001))['11'].runoff_volume;
  const reset=(await manager().reader.loadBaseWeppYearlyData(2000))['11'].runoff_volume;
  assert.equal(original,25);assert.equal(cached,25);assert.equal(newYear,76);assert.equal(reset,75);
  const result={original_year_2000:original,cached_year_2000_after_rewrite:cached,new_year_2001_after_rewrite:newYear,
    fresh_manager_year_2000:reset,requests:first.requests(),real_parquet:true,real_duckdb:true,
    scope:'Actual active module. Query transport calls real DuckDB against a disposable Parquet; no deployed browser/model job. Demonstrates mixed file generations within one manager, not a claimed global filesystem snapshot contract.'};
  fs.writeFileSync(path.join(__dirname,'gl_dashboard_generation_probe.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>fs.rmSync(temp,{recursive:true,force:true}));
