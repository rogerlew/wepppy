"""Compact executed-chain certificate from the independent localization receipt."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();assert not a.output.exists()
    r=json.loads(a.input.read_text());assert r['accepted_runtime_arithmetic_readback'] and r['full_period_replays']==4
    for p,h in r['bindings'].items():assert sha(p)==h,p
    lanes={(x['window'],x['mode']):x['reconstruction'] for x in r['results']}
    values=[]
    for ip in (1,2):
        first=[lanes['first_peak',mode] for mode in (0,1)]
        next_event=[lanes['next_runoff',mode] for mode in (0,1)]
        writes=[[x for x in lane['writeback'] if x['day']==233 and x['ofe']==ip] for lane in first]
        assert all(len(x)==1 for x in writes);off,on=[x[0] for x in writes]
        assert off['terminal']==3 and on['terminal']==2 and off['owner']==on['owner']==3
        assert off['assigned_post'][4:]==on['assigned_post'][4:] and off['total_length_m']==on['total_length_m']
        widths=[[x for x in lane['width'] if x['day']==233 and x['ofe']==ip] for lane in first]
        assert widths[0][0]['input'][2]==widths[1][0]['input'][2]
        friction=[[x for x in lane['friction'] if x['day']==243 and x['ofe']==ip][0] for lane in next_event]
        for j in (0,1):assert widths[j][-1]['output'][2]==friction[j]['input'][0]
        assert friction[0]['input'][1]==friction[1]['input'][1]
        assert friction[0]['input'][3:5]==friction[1]['input'][3:5]
        qinf=[[x for x in lane['qinf'] if x['day']==243 and x['ofe']==ip][0] for lane in next_event]
        aa,bb=[x['input'] for x in qinf]
        assert [i for i,(x,y) in enumerate(zip(aa,bb)) if x!=y]==[1]
        assert qinf[0]['shape'][0]==qinf[1]['shape'][0]
        assert qinf[0]['output'][0]!=qinf[1]['output'][0]
        values.append({'ofe':ip,'day233_terminal_off_on':[3,2],
            'day233_duration_off_on_s':[off['terminal_duration_s'],on['terminal_duration_s']],
            'day233_peak_off_on_mm_h':[x['assigned_post'][3]*3.6e6 for x in (off,on)],
            'day233_width_off_on_m':[x[-1]['output'][2] for x in widths],
            'day243_consumed_width_off_on_m':[x['input'][0] for x in friction],
            'day243_frcteq_off_on':[x['output'][5] for x in friction],
            'day243_effective_alpha_off_on_m_half_per_s':[x['input'][1] for x in qinf],
            'day243_qinf_only_changed_input':'effective alpha',
            'day243_qinf_output_off_on_mm':[x['output'][0]*1000 for x in qinf],
            'day243_runoff_on_minus_off_mm':(qinf[1]['output'][0]-qinf[0]['output'][0])*1000})
    out={'accepted_executed_model_coupling':True,'accepted_physical_routing_validation':False,
         'accepted_original_isolation':False,'accepted_parameterization':False,
         'scope':'Two full16yr mode histories, each replayed under two diagnostic selectors. This certificate verifies the first two upstream event links; not four independent scientific samples.',
         'native_runs_by_reviewer':0,'chain':values,
         'counts':{key:sum(len(x['reconstruction'][key]) for x in r['results']) for key in ('writeback','width','friction','alpha','qinf')},
         'next_recommended_study':'Fresh36-run nine-pair whole-hillslope response declaration; same RRC rule and original input/off/null/density/physical/magnitude gates, explicitly permitting documented endogenous coupling. Original failed campaign is not relabeled.',
         'limits':['No physical calibration of100mm roughness or legacy soil truth.','No physical validation of connected shared-duration routing.','Residue effects remain downstream association.','No annual magnitude outcome interpreted by this localization.'],
         'bindings':{str(p.resolve()):sha(p) for p in (a.input,Path(__file__))}}
    a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps({'executed_chain_verified':True,'upstream_ofes':2}))

if __name__=='__main__':main()
