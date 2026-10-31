"""Verify actual canonical-build artifacts against the retained D2 candidate."""
from pathlib import Path
import argparse,json,hashlib
RAW=Path('/workdir/wepppy/out/roads-native-funding-20261031')
HERE=Path(__file__).resolve().parent

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def inventory(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('panel',choices=['roads','disturbed','cedar']);args=ap.parse_args();panel=args.panel
    if panel=='roads':
        left=RAW/'D2-matrix840';right=RAW/'r3-matrix840';old=json.loads((left/'results.json').read_text());new=json.loads((right/'results.json').read_text());assert len(old)==len(new)==840
        mapping={json.dumps(r['case'],sort_keys=True):r for r in old};records=[]
        for r in new:
            previous=mapping[json.dumps(r['case'],sort_keys=True)];folder='-'.join(r['case'].values())
            assert r['inputs']==previous['inputs'] and r['outputs']==previous['outputs'],folder
            assert r['physical_pass'] and previous['physical_pass']
            for name,digest in r['outputs'].items():assert sha(right/'matrix-v1'/folder/'output'/name)==digest
            for name,digest in r['inputs'].items():assert sha(right/'matrix-v1'/folder/'runs'/name)==digest
            records.append(dict(case=r['case'],outputs=r['outputs'],inputs=r['inputs']))
        result=dict(panel=panel,cases=840,output_files=sum(len(r['outputs']) for r in new),input_files=sum(len(r['inputs']) for r in new),exact=True,reference_results_sha256=sha(left/'results.json'),candidate_results_sha256=sha(right/'results.json'),records=records)
    else:
        suffix='disturbed_matrix0' if panel=='disturbed' else 'candidate/off'
        left=RAW/('D2-'+panel)/suffix;right=RAW/('r3-'+panel)/suffix
        a=inventory(left/'output');b=inventory(right/'output');assert a==b,(panel,'output mismatch',[n for n in a.keys()|b.keys() if a.get(n)!=b.get(n)][:20])
        expected=768 if panel=='disturbed' else 6057;assert len(a)==expected,len(a)
        if panel=='cedar':
            assert json.loads((left/'inputs.json').read_text())==json.loads((right/'inputs.json').read_text())
            assert json.loads((right/'watershed.json').read_text())['success']
        else:
            inputs=lambda root:{p.name:sha(p) for p in (root/'runs').iterdir() if p.is_file() and p.suffix not in ['.err','.log']}
            old_inputs=inputs(left);new_inputs=inputs(right)
            assert old_inputs.keys()==new_inputs.keys()
            comment_changes={}
            for name in old_inputs:
                if old_inputs[name]==new_inputs[name]:continue
                assert name.endswith('.sol'),name
                before=(left/'runs'/name).read_bytes().splitlines(keepends=True)
                after=(right/'runs'/name).read_bytes().splitlines(keepends=True)
                prefix=b'#   Build Date: '
                old_dates=[line for line in before if line.startswith(prefix)]
                new_dates=[line for line in after if line.startswith(prefix)]
                assert len(old_dates)==len(new_dates)==1
                assert [line for line in before if not line.startswith(prefix)]==[line for line in after if not line.startswith(prefix)],name
                comment_changes[name]=dict(old_sha256=old_inputs[name],new_sha256=new_inputs[name],old_comment=old_dates[0].decode().strip(),new_comment=new_dates[0].decode().strip())
            assert len(comment_changes)==96

        result=dict(panel=panel,output_files=len(a),exact=True,sha256=a,reference=str(left),candidate=str(right))
        if panel=='disturbed':result.update(inputs_byte_identical=False,input_difference_scope='96 generated soil Build Date comments only; every other input byte equal; raw files unchanged',soil_timestamp_changes=comment_changes)
    (HERE/('final-'+panel+'-parity.json')).write_text(json.dumps(result,indent=2)+'\n')
    print({k:v for k,v in result.items() if k not in ['sha256','records']},flush=True)
if __name__=='__main__':main()
