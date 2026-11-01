"""Versioned read-only acceptance correction; invokes no model process."""
import argparse
import hashlib
import json
from pathlib import Path
import read_native_v2

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def inventory(root): return {str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
def main(campaign,fixtures,out):
    out.mkdir(); before=inventory(campaign)
    helper_before={str(p):sha(p) for p in [Path(__file__),Path(read_native_v2.__file__)]}
    fixture_before=sha(fixtures/'receipt.json')
    if fixture_before!='7e7197e1f4455075e8d177560a8a313720c408b17b70e165f26769ecc3ae7f7d': raise ValueError('Unaccepted fixture identity')
    original=json.loads((campaign/'receipt.json').read_text())
    produced=json.loads((fixtures/'receipt.json').read_text())
    panel=['84543623','84543461','84543462','87913598','85179904','85179901']
    if produced['panel']!=panel or [(r['chkey'],r['lane']) for r in original['cases']]!=[(k,l) for k in panel for l in ['baseline','candidate']]: raise ValueError('Exact campaign support')
    results=[]
    for r in original['cases']:
        if r['returncode']!=0 or not r['completion']: raise ValueError('Native execution incomplete')
        if r['fixture_receipt_sha256']!=fixture_before: raise ValueError('Original fixture binding')
        root=campaign/(r['chkey']+'-'+r['lane'])
        if sha(root/'runs/stdout')!=r['stdout_sha256'] or sha(root/'runs/stderr')!=r['stderr_sha256']: raise ValueError('Process log drift')
        fixture=next(x for x in produced['cases'] if x['id']=='source-'+r['chkey'])[r['lane']]
        if sha(root/'source.sol')!=fixture['sha256']: raise ValueError('Fixture mismatch')
        if any(sha(root/'runs'/n)!=v for n,v in r['inputs'].items()): raise ValueError('Consumed input drift')
        record=dict(chkey=r['chkey'],lane=r['lane'])
        try: record.update(read_native_v2.read(root,fixture))
        except (ValueError,KeyError,OSError,ZeroDivisionError,OverflowError) as error: record.update(passed=False,error=str(error))
        results.append(record)
    pairs=[]
    for key in produced['panel']:
        rows=[r for r in results if r['chkey']==key]
        if len(rows)!=2: raise ValueError('Pair support')
        if all(r['passed'] for r in rows):
            changed=[n for n,v in rows[0]['output_hashes'].items() if rows[1]['output_hashes'][n]!=v]
            if key=='84543623' and changed: raise ValueError('Zero-rock output drift')
            if rows[0]['native_depth_mm']!=rows[1]['native_depth_mm']: raise ValueError('Paired support mismatch')
            pairs.append(dict(chkey=key,changed_outputs=changed))
    if inventory(campaign)!=before: raise ValueError('Readback mutated campaign')
    if sha(fixtures/'receipt.json')!=fixture_before or any(sha(p)!=v for p,v in helper_before.items()): raise ValueError('Reader/fixture changed')
    result=dict(passed=all(r['passed'] for r in results),cases=results,comparisons=pairs,
        campaign_inventory=before,original_campaign_unchanged=True,
        helper_hashes={p.name:sha(p) for p in [Path(__file__),Path(read_native_v2.__file__)]},
        correction='Native INPUT adds200mm before1800cap; observations ordered perOFE SCON thenWB. Original failed reader/declaration retained.',
        no_model_rerun=True)
    (out/'receipt.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(passed=result['passed'],cases=len(results),errors=[r for r in results if not r['passed']])))
    if not result['passed']: raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();main(a.campaign,a.fixtures,a.out)
