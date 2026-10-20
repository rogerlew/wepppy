"""Execute payloads emitted by both real dashboard ET query builders in DuckDB."""
import json
from pathlib import Path
import subprocess

import duckdb
import pandas as pd
import pytest

pytestmark = pytest.mark.integration


def emitted_payloads(mode='event_ET'):
    module = Path(__file__).parents[2] / 'wepppy/weppcloud/static/js/gl-dashboard/data/wepp-data.js'
    script = r'''
import fs from 'node:fs';
const {createWeppDataManager} = await import('data:text/javascript;base64,' + fs.readFileSync(process.argv[1]).toString('base64'));
const payloads = [];
const state = {weppEventSelectedDate:'2001-01-01', comparisonMode:true, currentScenarioPath:'scenario', baseSummaryCache:{}};
const response = {records:[{topaz_id:101,value:null}]};
globalThis.fetch = async (url, options) => { payloads.push(JSON.parse(options.body)); return {ok:true,json:async()=>response}; };
const manager = createWeppDataManager({ctx:{runid:'test',config:'cfg'},getState:()=>state,
 setValue:(k,v)=>{state[k]=v;},setState:v=>Object.assign(state,v),
 postQueryEngine:async p=>{payloads.push(p);return response;},
 pickActiveWeppEventLayer:()=>({mode:process.argv[2]}),WEPP_EVENT_WAT_PATH:'H.wat.parquet'});
await manager.refreshWeppEventData();
const ranges = manager.computeWeppEventRanges({'1':{event_ET:null},'2':{event_ET:5}});
state.weppEventSummary = {'1':{event_ET:null},'2':{event_ET:5}};
state.baseSummaryCache.weppEvent = {'1':{event_ET:7},'2':{event_ET:6}};
const diffs = manager.computeWeppEventDiffRanges();
console.log(JSON.stringify({payloads,ranges,diffs}));
'''
    result = subprocess.run(['node', '--input-type=module', '-e', script, str(module), mode],
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


@pytest.fixture(scope='module')
def payloads():
    return emitted_payloads()


@pytest.mark.parametrize('area,expected', [(250., 5.), (0., None), (-1., None), (None, None), (float('inf'), None)])
def test_selected_and_comparison_sql_use_local_area(payloads, area, expected):
    wat = pd.DataFrame({'wepp_id':[1,1], 'Area':[area,750.], 'Ep':[1.,4.], 'Es':[.5,1.], 'Er':[.5,1.]})
    hill = pd.DataFrame({'wepp_id':[1], 'topaz_id':[101]})
    assert len(payloads['payloads']) == 2
    with duckdb.connect() as conn:
        conn.register('wat',wat); conn.register('hill',hill)
        for payload in payloads['payloads']:
            sql = payload['aggregations'][0]['sql']
            value = conn.execute(f'SELECT {sql} FROM wat JOIN hill USING(wepp_id) GROUP BY hill.topaz_id').fetchone()[0]
            assert value == expected
            assert [f['value'] for f in payload['filters']] == [2001,1,1]
    assert payloads['ranges']['event_ET']['min'] == 5
    assert payloads['diffs']['event_ET']['max'] == 1


@pytest.mark.parametrize('mode,expected',[('event_P',16.),('event_Q',4.)])
def test_physical_water_generated_selected_and_base_sql(mode,expected):
    payloads=emitted_payloads(mode)['payloads']
    wat=pd.DataFrame(dict(wepp_id=[1,1,2],ofe_id=[1,2,1],Area=[250.,750.,2000.],
        year=[2001]*3,month=[1]*3,day_of_month=[1]*3,P=[2.,10.,20.],Q=[99.,8.,2.]))
    hill=pd.DataFrame(dict(wepp_id=[1,2],topaz_id=[101,101]))
    with duckdb.connect() as conn:
        conn.register('__wepp_source_0',wat);conn.register('hill',hill)
        for payload in payloads:
            expression=payload['aggregations'][0]['sql']
            sql=f'SELECT {expression} FROM __wepp_source_0 wat JOIN hill USING(wepp_id) WHERE wat.day_of_month=1 GROUP BY hill.topaz_id'
            assert conn.execute(sql).fetchone()[0]==expected


def test_dashboard_known_terminal_absence_is_unavailable():
    payloads=emitted_payloads('event_Q')['payloads']
    wat=pd.DataFrame(dict(wepp_id=[1,1,1],ofe_id=[1,2,1],Area=[250.,750.,250.],
        year=[2001]*3,month=[1]*3,day_of_month=[1,1,2],Q=[4.,8.,7.]))
    hill=pd.DataFrame(dict(wepp_id=[1],topaz_id=[101]))
    with duckdb.connect() as conn:
        conn.register('__wepp_source_0',wat);conn.register('hill',hill)
        for payload in payloads:
            expression=payload['aggregations'][0]['sql']
            value=conn.execute(f'SELECT {expression} FROM __wepp_source_0 wat JOIN hill USING(wepp_id) WHERE wat.day_of_month=2 GROUP BY hill.topaz_id').fetchone()[0]
            assert value is None


def test_missing_and_duplicate_terminals_do_not_cancel_after_mapping():
    wat = pd.DataFrame(dict(wepp_id=[1,1,1,2,2], ofe_id=[1,2,1,1,1],
        Area=[250.,750.,250.,1000.,1000.], year=[2001]*5, month=[1]*5,
        day_of_month=[1,1,2,2,2], Q=[4.,8.,7.,2.,2.]))
    hill = pd.DataFrame(dict(wepp_id=[1,2], topaz_id=[101,101]))
    with duckdb.connect() as conn:
        conn.register('__wepp_source_0', wat)
        conn.register('hill', hill)
        for payload in emitted_payloads('event_Q')['payloads']:
            expression = payload['aggregations'][0]['sql']
            assert conn.execute(f'SELECT {expression} FROM __wepp_source_0 wat JOIN hill USING(wepp_id) WHERE wat.day_of_month=2 GROUP BY hill.topaz_id').fetchone()[0] is None
