"""Summarize observed coarse boundary changes without assigning hidden fluxes."""
import argparse,json,math
from pathlib import Path
from audit_resets_v2 import sha

def main(root,out):
    result=[]
    for scenario in ['zero-ks1','normal-ks1','high-ks1']:
        folder=root/'retained-v2'/scenario
        receipt=json.loads((folder/'receipt.json').read_text())
        reset_rows=[json.loads(line) for line in (folder/'resets.jsonl').open()]
        resets={(r['event']['map'],r['layer']):r for r in reset_rows}
        sequences={}
        for line in (folder/'sequences.jsonl').open():
            row=json.loads(line)
            for identifier in row['clearing_ids']:sequences.setdefault(identifier,[]).append(row)
        clears=json.loads(Path(f'out/frozen-water-history-20261101/all-clearing-v3/{scenario}/receipt.json').read_text())['clears']
        chains=[]
        for clear in clears:
            identifier=clear['id'];rows=sequences[identifier]
            if rows[0]['tag']!='MAP_POST' or rows[-1]['tag']!='INIT_POST':raise ValueError('Incomplete chain endpoints')
            pending=None;water=[];reset_hits=[]
            for row in rows:
                tag=row['tag'];c=row['coarse']
                if tag in {'WB_PRE','IRS_WB_PRE'}:
                    if pending is not None:raise ValueError('Nested water boundary')
                    pending=row
                elif tag in {'WB_POST','IRS_WB_POST'}:
                    if pending is None or tag!=pending['tag'].replace('PRE','POST'):raise ValueError('Unmatched water boundary')
                    if any(row['event'][k]!=pending['event'][k] for k in ('year','day','ofe')):raise ValueError('Water boundary clock drift')
                    before=pending['coarse'];water.append(dict(before_event=pending['event'],after_event=row['event'],
                        ST_before=before['st'],ST_after=c['st'],net_ST_change_m=c['st']-before['st'],
                        YST_before=before['yst'],YST_after=c['yst'],
                        interpretation='Net coarse stock change across full water-balance call; constituent accepted fluxes unobserved'))
                    pending=None
                elif tag=='MAP_PRE' and (row['event']['map'],row['layer']) in resets:
                    reset=resets[row['event']['map'],row['layer']]
                    reset_hits.append(dict(event=row['event'],nominal_residual_m=reset['nominal_residual_m'],
                        inherited_reference_mismatch_m=reset['inherited_reference_mismatch_m'],fine_change_m=reset['fine_change_m'],
                        YST_change_since_clear_m=c['yst']-rows[0]['coarse']['yst'],
                        fine_change_since_clear_m=row['fine']['total']-rows[0]['fine']['total']))
            if pending is not None:raise ValueError('Unfinished water boundary')
            chains.append(dict(id=identifier,clear_event=clear['event'],cleared_m=clear['cleared_m'],
                next_initialization=rows[-1]['event'],observed_boundaries=len(rows),water_balance_calls=water,zero_resets=reset_hits))
        peak=max(reset_rows,key=lambda x:x['nominal_residual_m'])
        result.append(dict(scenario=scenario,counts=receipt['counts'],ranges=receipt['ranges'],
            invalid_flag_counts={key:sum(r[key] for r in reset_rows) for key in ['negative_fine_cell','negative_nw','invalid_geometry','negative_fine_component','negative_coarse_component']},
            peak_reset=peak,chains=chains,reset_rows_sha256=sha(folder/'resets.jsonl'),sequences_sha256=sha(folder/'sequences.jsonl')))
    with out.open('x') as stream:json.dump(dict(cases=result),stream,indent=2,allow_nan=False);stream.write('\n')
    for r in result:
        hits=[c for c in r['chains'] if any(z['event']['map']==r['peak_reset']['event']['map'] for z in c['zero_resets'])]
        print(r['scenario'],'chains',len(r['chains']),'linked_peak',[c['id'] for c in hits],'flags',r['invalid_flag_counts'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.root,a.out)
