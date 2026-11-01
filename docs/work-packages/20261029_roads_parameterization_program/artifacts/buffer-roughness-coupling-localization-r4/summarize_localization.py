"""Compact source-free readback of the accepted four-replay localization."""
from pathlib import Path
import argparse,hashlib,json

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--review',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 d=json.loads(a.review.read_text());assert d['accepted_runtime_arithmetic_readback'] and d['full_period_replays']==4
 assert not d['accepted_original_isolation'] and not d['accepted_parameterization']
 for path,h in d['bindings'].items():assert sha(path)==h,path
 a.output.mkdir(parents=True,exist_ok=False)
 inputs={str(a.review.resolve()):sha(a.review),str(Path(__file__).resolve()):sha(__file__),**d['bindings']}
 save(a.output/'declaration.json',dict(scope=__doc__,inputs=inputs,selection='All three OFEs from day233 writeback/width; first native day243 hydrology friction/ALPHA/QINF call for both upstream OFEs. All four replay call counts retained. No new native run or model calculation.'))
 first=[];second=[];counts=[]
 for r in d['results']:
  mode=r['mode'];rec=r['reconstruction'];counts.append(dict(window=r['window'],mode=mode,trace_rows=r['trace_rows'],producers={k:len(v) for k,v in rec.items()}))
  if r['window']=='first_peak':
   for ip in (1,2,3):
    wb=[x for x in rec['writeback'] if x['day']==233 and x['ofe']==ip];ww=[x for x in rec['width'] if x['day']==233 and x['ofe']==ip]
    assert len(wb)==1 and ww
    x=wb[0];first.append(dict(mode=mode,ofe=ip,owner=x['owner'],terminal=x['terminal'],
       duration_s=x['assigned_post'][2],peak_mm_h=x['assigned_post'][3]*3.6e6,
       native_equivalent_runoff_m=x['assigned_post'][4],width_before_first_shear_m=ww[0]['input'][2],
       width_after_last_shear_m=ww[-1]['output'][2]))
  else:
   for ip in (1,2):
    al=[x for x in rec['alpha'] if x['day']==243 and x['ofe']==ip];qq=[x for x in rec['qinf'] if x['day']==243 and x['ofe']==ip]
    assert al and qq
    x=al[0];fr=next(v for v in rec['friction'] if v['line']==x['friction_line']);q=qq[0]
    second.append(dict(mode=mode,ofe=ip,consumed_width_m=fr['input'][0],rspace_m=fr['input'][1],rillar=fr['input'][2],
       interrill_friction=fr['input'][3],rill_friction=fr['input'][4],equivalent_friction=fr['output'][5],
       alpha_m_half_per_s=x['values'][0],qinf_inputs=q['input'],qinf_output_m=q['output'][0],
       qinf_recession_reduction_m=q['recession_reduction_m']))
 delta=[];names=['incoming_runoff_m','effective_alpha_m_half_per_s','effective_length_m','conductivity_m_s','rainfall_excess_duration_s','terminal_infiltration_rate_m_s']
 for ip in (1,2):
  off=next(r for r in second if r['ofe']==ip and r['mode']==0);on=next(r for r in second if r['ofe']==ip and r['mode']==1)
  changed=[n for n,x,y in zip(names,off['qinf_inputs'],on['qinf_inputs']) if x!=y]
  assert changed==['effective_alpha_m_half_per_s']
  delta.append(dict(ofe=ip,changed_qinf_inputs=changed,adjusted_runoff_on_minus_off_mm=1000*(on['qinf_output_m']-off['qinf_output_m'])))
 assert len(d['cross_window_width_values'])==4 and all(x['exact'] for x in d['cross_window_width_values'])
 summary=dict(accepted_scope='Observed whole-hillslope routing feedback in one selected modern profile, two windows, same single RRC intervention.',
   original_counterfactual_campaign='Failed upstream isolation;32remaining runs not executed.',
   native_replays=4,ordinary_outputs_exact=28,full_state_traces_exact=4,first_peak=first,next_runoff=second,
   qinf_mode_differences=delta,cross_window_width_values=d['cross_window_width_values'],call_support=counts,
   exact_arithmetic=['IRS duration assignment and peak recomputation','SHEARS selection/max/spacing cap using observed native candidate','FRCTEQ linear combination','RDAT ALPHA square-root expression'],
   observed_not_independently_solved=['SHEARS width power-law candidate','QINF nonlinear recession-infiltration law'],
   limits=['Native producer support may differ between modes; absent calls are not zero values.','Stored pre-writeback values need not represent independently computed upstream hydrographs.','No physical validation of shared-duration routing or100mm roughness.','No direct decomposition/residue attribution.','No annual magnitude acceptance or whole-nine-pair claim.'],
   review_sha256=sha(a.review),declaration_sha256=sha(a.output/'declaration.json'))
 save(a.output/'summary.json',summary)
 lines=['| Day233, upstream role | Shared duration, s off→on | Peak, mm/h off→on | Persisted width, mm off→on |','| --- | ---: | ---: | ---: |']
 for ip,role in ((1,'Road'),(2,'Fill')):
  off=next(r for r in first if r['ofe']==ip and r['mode']==0);on=next(r for r in first if r['ofe']==ip and r['mode']==1)
  lines.append(f"| {role} | {off['duration_s']:.6f} → {on['duration_s']:.6f} | {off['peak_mm_h']:.6f} → {on['peak_mm_h']:.6f} | {off['width_after_last_shear_m']*1000:.6f} → {on['width_after_last_shear_m']*1000:.6f} |")
 lines+=['','| Day243, upstream role | Equivalent friction off→on | ALPHA, m½/s off→on | QINF adjusted runoff, mm off→on |','| --- | ---: | ---: | ---: |']
 for ip,role in ((1,'Road'),(2,'Fill')):
  off=next(r for r in second if r['ofe']==ip and r['mode']==0);on=next(r for r in second if r['ofe']==ip and r['mode']==1)
  lines.append(f"| {role} | {off['equivalent_friction']:.9f} → {on['equivalent_friction']:.9f} | {off['alpha_m_half_per_s']:.9f} → {on['alpha_m_half_per_s']:.9f} | {off['qinf_output_m']*1000:.9f} → {on['qinf_output_m']*1000:.9f} |")
 (a.output/'paired-observations.md').write_text('\n'.join(lines)+'\n')
 assert all(sha(path)==h for path,h in inputs.items())
 print(json.dumps(dict(passed=True,runs=4,ordinary_files=28,observed_width_transfers_exact=4,only_qinf_input_changed='effective ALPHA')))
if __name__=='__main__':main()
