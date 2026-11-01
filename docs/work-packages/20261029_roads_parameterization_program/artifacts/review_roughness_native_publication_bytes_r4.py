"""Bounded LF/staged-byte publication delta; never mutates retained evidence."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,io,json,subprocess,tarfile

REPO=Path('/workdir/wepppy').resolve()
ART=REPO/'docs/work-packages/20261029_roads_parameterization_program/artifacts'
RAW=REPO/'out/roads-parameterization-program-20261031'
SUP=RAW/'native-roughness-document-publication-r4'
NATIVE=Path('/workdir/wepp-forest-release-20261009').resolve()
INC=NATIVE/'docs/ablation/20261031_roads_buffer_roughness_counterfactual'
CSV_FILES={'matrix.csv','artifacts/logs/contract_observations.csv','artifacts/logs/matrix-before-whole-hillslope-response.csv'}

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_text())
def inventory(root):return {str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
def csv_rows(path):return list(csv.reader(io.StringIO(Path(path).read_text(newline=''))))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();assert not args.output.exists()
    old_receipt=ART/'buffer-roughness-hillslope-response-r4-native-incident-review.json'
    old=read(old_receipt);before=SUP/'before-lf-normalization';after=SUP/'after-lf-normalization'
    original=inventory(before);current=inventory(INC);retained=inventory(after)
    assert original=={r['path']:r['sha256'] for r in old['native_public_allowlist']}
    assert current==retained and set(current)==set(original) and len(current)==12
    changed={n for n in current if current[n]!=original[n]}
    assert changed==CSV_FILES|{'artifacts/manifest.csv','artifacts/checksums.sha256'}
    line_changes=[]
    for n in sorted(CSV_FILES):
        a,b=(before/n).read_bytes(),(after/n).read_bytes();assert a.replace(b'\r\n',b'\n')==b and b'\r\n' not in b
        with (before/n).open(newline='') as f:left=list(csv.reader(f))
        with (after/n).open(newline='') as f:right=list(csv.reader(f))
        assert left==right
        line_changes.append(dict(path=n,before_sha256=original[n],after_sha256=current[n],crlf_pairs_removed=a.count(b'\r\n'),logical_csv_rows=len(left),logical_rows_exact=True))
    with (before/'artifacts/manifest.csv').open(newline='') as f:left=list(csv.DictReader(f))
    with (after/'artifacts/manifest.csv').open(newline='') as f:right=list(csv.DictReader(f))
    assert len(left)==len(right);timestamp_cells=[]
    for a,b in zip(left,right,strict=True):
        assert a.keys()==b.keys()
        for field in a:
            if a[field]==b[field]:continue
            assert field=='created_utc' and a['relative_path']==b['relative_path'] and b['relative_path'] in CSV_FILES-{'matrix.csv'}
            produced=datetime.fromtimestamp((INC/b['relative_path']).stat().st_mtime,timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            assert b[field]==produced
            timestamp_cells.append(dict(path=b['relative_path'],field=field,before=a[field],after=b[field],matches_current_producer_file_mtime=True))
    assert len(timestamp_cells)==2
    sums={}
    for line in (INC/'artifacts/checksums.sha256').read_text().splitlines():
        h,n=line.split(None,1);n=n.strip();assert n not in sums and sha(INC/n)==h;sums[n]=h
    assert set(sums)|{'artifacts/checksums.sha256'}==set(current)
    attrs=subprocess.run(['git','check-attr','text','eol','--',*[str((INC/n).relative_to(NATIVE)) for n in sorted(CSV_FILES)]],cwd=NATIVE,capture_output=True,text=True,check=True).stdout
    assert attrs.count(': text: set')==3 and attrs.count(': eol: lf')==3
    staged=subprocess.run(['git','diff','--cached','--name-only','-z'],cwd=NATIVE,capture_output=True,check=True).stdout.split(b'\0');staged=[p.decode() for p in staged if p]
    assert set(staged)=={str((INC/n).relative_to(NATIVE)) for n in current}
    blob_hashes={}
    for n in staged:
        blob=subprocess.run(['git','show',':'+n],cwd=NATIVE,capture_output=True,check=True).stdout
        h=hashlib.sha256(blob).hexdigest();assert h==sha(NATIVE/n);blob_hashes[n]=h
    assert subprocess.run(['git','diff','--name-only'],cwd=NATIVE,capture_output=True,text=True,check=True).stdout==''
    policy=subprocess.run(['python','tools/check_ablation_artifact_policy.py'],cwd=NATIVE,capture_output=True,text=True);assert policy.returncode==0
    rp=ART/'revision4-native-roughness-document-publication-retention.json';r=read(rp);archive=Path(r['archive']);assert sha(archive)==r['sha256'] and archive.stat().st_size==r['bytes']
    mp=Path(str(archive)+'.manifest.json');assert sha(mp)==r['manifest_sha256'];manifest=read(mp);assert len(manifest)==r['files']==25
    assert {str((SUP/n).relative_to(RAW)):h for n,h in inventory(SUP).items()}==manifest
    assert read(Path(str(archive)+'.aliases.json'))==r['omitted_aliases']=={}
    seen={};size=0
    with tarfile.open(archive,'r|gz') as stream:
        for member in stream:
            assert member.isfile() and member.name not in seen and not member.name.startswith('/') and '..' not in Path(member.name).parts
            file=stream.extractfile(member);assert file is not None;seen[member.name]=hashlib.file_digest(file,'sha256').hexdigest();size+=member.size
    assert seen==manifest and size==r['uncompressed_bytes']
    assert inventory(before)==original and inventory(after)==inventory(INC)==current
    predecessor=ART/'buffer-roughness-hillslope-response-r4-checkpoint-review.json';assert sha(predecessor)=='3f88138b1948fc3b7fa90e7e13a7277dd08fd45f7c608ed023066d03020283ab'
    assert sha(old_receipt)=='a155e580441133f0f40d69de19bd69669feeb9a03dfe2a0b979a9fe2cac85a01'
    assert sha(ART/'candidate-ledger-v20.json')=='94687c2a6d693543758431c084820d939da165b8db25a4a072257daa5bcff39f'
    assert sha(ART/'buffer-roughness-hillslope-response-r4/manifest.json')=='b81e3bae199037e737e9aab730408f25130774b124024d3dae12a62db40b09fe'
    bindings=[old_receipt,predecessor,rp,ART/'candidate-ledger-v20.json',ART/'buffer-roughness-hillslope-response-r4/manifest.json',SUP/'normalization.json',Path(__file__).resolve(),NATIVE/'.gitattributes',NATIVE/'tools/check_ablation_artifact_policy.py']
    report=dict(accepted_native_publication_v2=True,blocking_findings=[],scope='Additive packaging-only correction to native source-free incident publication. Supersedes only the current native working/staged-byte allowlist; prior reviews remain valid historical evidence for the preserved before-normalization packet.',scientific_or_numeric_data_changed=False,native_model_executions=0,canonical_native_source_or_binary_changed=False,csv_line_ending_changes=line_changes,generated_manifest_timestamp_cells=timestamp_cells,manifest_other_logical_cells_unchanged=True,current_checksums_exact=True,staged_native_files=12,all_staged_blob_bytes_equal_working_tree=True,existing_eol_policy_enforced=True,artifact_policy=dict(returncode=0,stdout=policy.stdout,stderr=policy.stderr),supplementary_retention=dict(archive_sha256=r['sha256'],manifest_sha256=r['manifest_sha256'],files=25,all_member_names_and_bytes_verified=True,raw_inventory_exact=True),preserved_prior_native_packet=str(before),predecessor_receipts_unchanged=True,primary_ledger_and_public_scientific_packet_unchanged=True,raw_writer_clear=True,native_public_allowlist=[dict(path=n,sha256=h) for n,h in sorted(current.items())],staged_native_blobs=blob_hashes,bindings={str(p.resolve()):sha(p) for p in bindings})
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'accepted':True,'staged_files':12,'line_ending_files':3,'generated_timestamp_cells':2,'supplement_archive_members':25,'receipt_sha256':sha(args.output)}))

if __name__=='__main__':main()
