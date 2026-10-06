"""Supplement, never overwrite, historical replay with source-checked operands.

Pinned IRS lines 632-646 replace remax with s(1) in the no-positive-excess
surplus branch. The observer retains pdremax from before this replacement.
This supplement applies only to the reviewed single-OFE packets.
"""
import json
import pandas as pd
from study import ROOT, dump
from peakflow_phase1_replay import run_driver, app_diagnostics, verify_packet

records=[]
for path in sorted((ROOT/'analysis/manual').glob('*/packet.json')):
    packet=json.loads(path.read_text());verify_packet(packet)
    scalar=packet['scalars'];mode=scalar['surplus_assignment_mode']
    assert scalar['ofe']==1 and scalar['solver_call_ordinal']==1
    actual_remax=scalar['remax_pre_surplus_m_s']
    reason='positive-excess branch retains pre-surplus remax'
    if mode in ('storm','upstream','fallback_24h'):
        assert scalar['ns']==1
        assert packet['production']['selected_solver']=='APPMTH'
        actual_remax=scalar['surplus_added_rate_m_s']
        assert abs(actual_remax-packet['post_surplus_forcing'][0]['rate_m_s'])<1e-12
        reason='IRS no-positive-excess branch assigns remax=s(1)=surpls/durre'
    else:assert mode=='positive_excess'
    result=run_driver(ROOT/'bin/peak_replay',packet,actual_remax)
    key='appmth_peak_m_s' if packet['production']['selected_solver']=='APPMTH' else 'hdrive_peak_m_s'
    delta=abs(result[key]-packet['production']['peak_m_s'])
    assert delta<=5e-11,(packet['event_id'],delta)
    diagnostics=app_diagnostics(scalar,actual_remax)
    report={'schema_version':1,'source_commit':'ea25ad79ef7dab20206bca095b2958786f5ae317',
            'source_reference':'src/irs.for:594-653 and 775-791',
            'event_id':packet['event_id'],'packet_sha256':packet['payload_sha256'],
            'operand_derivation':reason,'remax_supplied_m_s':actual_remax,
            'selected_method_delta_m_s':delta,'status':'pass',
            'replay':result,'appmth_diagnostics':diagnostics,
            'scope':'post-hoc source-checked single-OFE production operand replay; not harmonized forcing or a model repair'}
    dump(path.parent/'production-operand-replay.json',report)
    records.append({'event_id':packet['event_id'],'surplus_assignment_mode':mode,
        'original_replay_status':'pass' if (path.parent/'replay.json').exists() else 'unresolved',
        'branch_replay_status':'pass','selected_method_delta_m_s':delta,
        'remax_recorded_pre_surplus_m_s':scalar['remax_pre_surplus_m_s'],
        'remax_supplied_m_s':actual_remax,'production_peak_mm_h':packet['production']['peak_m_s']*3600000,
        'branch_appmth_mm_h':result['appmth_peak_m_s']*3600000,
        'branch_hdrive_mm_h':result['hdrive_peak_m_s']*3600000,'branch_vstar':diagnostics['vstar']})
pd.DataFrame(records).to_csv(ROOT/'analysis/manual-branch-replay.csv',index=False)
print(json.dumps({'reviewed_lane_cases':len(records),'branch_replay_pass':len(records),
     'max_selected_delta_m_s':max(r['selected_method_delta_m_s'] for r in records)}))
