"""Exact source-free checkpoint and archive closure review; no native execution."""
from pathlib import Path
import argparse,hashlib,json,subprocess,tarfile

REPO=Path('/workdir/wepppy').resolve()
ART=REPO/'docs/work-packages/20261029_roads_parameterization_program/artifacts'
RAW=REPO/'out/roads-parameterization-program-20261031'
NATIVE=Path('/workdir/wepp-forest-release-20261009').resolve()
INC=NATIVE/'docs/ablation/20261031_roads_buffer_roughness_counterfactual'

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_text())

def archive_check():
    path=ART/'revision4-buffer-roughness-hillslope-response-retention.json';r=read(path);archive=Path(r['archive'])
    assert archive.stat().st_size==r['bytes'] and sha(archive)==r['sha256']
    mp=Path(str(archive)+'.manifest.json');assert sha(mp)==r['manifest_sha256'];manifest=read(mp)
    assert len(manifest)==r['files']==6908
    assert read(Path(str(archive)+'.aliases.json'))==r['omitted_aliases']=={}
    roots=['buffer-roughness-hillslope-response-r4','buffer-roughness-hillslope-interpretation-r4']
    actual={str(p.relative_to(RAW)):sha(p) for root in roots for p in (RAW/root).rglob('*') if p.is_file()}
    assert actual==manifest,('raw closure',set(actual)^set(manifest))
    seen={};size=0
    with tarfile.open(archive,'r|gz') as stream:
        for member in stream:
            assert member.isfile() and member.name not in seen
            assert not member.name.startswith('/') and '..' not in Path(member.name).parts
            f=stream.extractfile(member);assert f is not None
            seen[member.name]=hashlib.file_digest(f,'sha256').hexdigest();size+=member.size
    assert seen==manifest and size==r['uncompressed_bytes']
    assert sha(archive)==r['sha256']
    return dict(files=6908,archive_sha256=r['sha256'],manifest_sha256=r['manifest_sha256'],uncompressed_bytes=size,all_archive_member_bytes_rehashed=True,exact_archive_membership=True,exact_raw_tree_closure=True,roots=roots,receipt_sha256=sha(path))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();assert not args.output.exists()
    ledger_path=ART/'candidate-ledger-v20.json';ledger=read(ledger_path);lh=sha(ledger_path)
    assert ledger['version']==20 and ledger['status']=='no_parameter_candidate_accepted'
    assert ledger['withheld_materials_untouched'] and ledger['ui_specification_and_layout_human_gate_preserved'] and not ledger['production_defaults_changed']
    assert sha(ART/ledger['predecessor']['path'])==ledger['predecessor']['sha256']
    for name,h in ledger['evidence_sha256'].items():assert sha(ART/name)==h,name
    x=ledger['roughness_whole_hillslope_response']
    assert (x['u1_valid_native_histories_retained'],x['u1_remaining_histories_not_executed'],x['u2_fresh_full_period_runs'])==(4,32,36)
    assert (x['off_reference_histories_exact'],x['predicted_null_pairs_exact'],x['active_modern_histories'])==(18,12,6)
    assert (x['native_output_files_reviewed'],x['full_state_rows_reviewed'],x['derived_tables_compared_exact'],x['copied_audit_nonmutation_passes'],x['verifier_receipts'])==(252,4931676,144,44,88)
    assert x['selected_panel_improvement_criterion'] and x['primary_b1_b2_b3_remain_failed'] and x['three_underprediction_controls_unchanged']
    assert not any(x[k] for k in ('sufficient_remedy','roughness_100mm_physically_validated','routing_law_physically_validated','parameter_promotion'))
    science=read(ART/'buffer-roughness-hillslope-response-r4-scientific-acceptance.json')
    assert science['accepted_model_sensitivity_dataset'] and science['accepted_prespecified_selected_panel_improvement'] and not science['accepted_parameterization']
    assert x['recovered_modern_cases']==science['recovery'] and x['regressed_original_passing_modern_cases']==science['regressions']
    for a,b in zip(x['modern_annual_cases'],science['modern_annual_responses'],strict=True):
        assert a['stratum']==b['stratum'] and a['reference_kg_yr']==b['reference_kg_yr'] and a['off_on_kg_yr']==b['annual_off_on_kg_yr'] and a['original_envelope_off_on_pass']==b['original_envelope_off_on_pass']
    packet=ART/'buffer-roughness-hillslope-response-r4';manifest=read(packet/'manifest.json')
    assert {p.name for p in packet.iterdir() if p.is_file()}==set(manifest['files'])|{'manifest.json'}
    for name,h in manifest['files'].items():assert sha(packet/name)==h
    pub=read(ART/'buffer-roughness-hillslope-response-r4-publication-review.json');assert pub['accepted_public_packet'] and pub['accepted_reproduction'] and pub['accepted_private_source_disclosure_boundary']
    assert sha(packet/'manifest.json')==pub['final_manifest_sha256']
    for p,h in pub['bindings'].items():assert sha(p)==h,p
    native=read(ART/'buffer-roughness-hillslope-response-r4-native-incident-review.json');assert native['accepted_native_source_free_incident'] and native['artifact_policy']['returncode']==0
    for row in native['native_public_allowlist']:assert sha(INC/row['path'])==row['sha256'],row['path']
    docs=[REPO/'PROJECT_TRACKER.md',ART.parent/'package.md',ART.parent/'tracker.md',ART.parent/'prompts/active/program_execplan.md',REPO/'docs/standards/generated-artifact-validation-standard.md']
    assert all('36' in p.read_text() for p in docs[:4]);assert '### Preserve Accepted Evidence During Verification' in docs[-1].read_text()
    archive=archive_check()
    staged=subprocess.run(['git','diff','--cached','--name-only','-z'],cwd=REPO,capture_output=True,check=True).stdout.split(b'\0')
    staged=[REPO/p.decode() for p in staged if p]
    for p in staged:
        blob=subprocess.run(['git','show',':'+str(p.relative_to(REPO))],cwd=REPO,capture_output=True,check=True).stdout
        assert hashlib.sha256(blob).hexdigest()==sha(p)
        assert p.suffix in {'.md','.py','.json'}
    extras=[ART/'buffer-roughness-hillslope-response-r4-native-incident-review.json',Path(__file__).resolve()]
    allow=sorted(set(staged+extras));assert all(p==REPO/'PROJECT_TRACKER.md' or p.is_relative_to(ART.parent) or p==docs[-1] for p in allow)
    assert sha(ledger_path)==lh
    report=dict(accepted_checkpoint=True,blocking_findings=[],ledger_sha256=lh,ledger_evidence_hashes_verified=len(ledger['evidence_sha256']),archive=archive,public_packet_manifest_sha256=sha(packet/'manifest.json'),public_allowlist=[dict(path=str(p.relative_to(REPO)),sha256=sha(p)) for p in allow],native_incident_review_sha256=sha(ART/'buffer-roughness-hillslope-response-r4-native-incident-review.json'),native_public_allowlist=native['native_public_allowlist'],living_docs_and_standard_reviewed=[str(p.relative_to(REPO)) for p in docs],scope='Completed36-history whole-hillslope sensitivity checkpoint, four valid prior whole-hillslope histories retained separately, and source-free incident history. No production parameter/source/binary change or physical-validity acceptance.',residual_limits=['Primary small-reference failures and three underprediction controls remain unresolved.','100 mm roughness and shared-routing physical validity remain unproven.','Next step is retained storage/epoch decomposition; full-matrix, withheld and human UI gates remain outstanding.'],raw_writer_clear=True,native_model_runs_by_reviewer=0)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'accepted_checkpoint':True,'archive_members':6908,'public_allowlist_files':len(allow),'ledger_sha256':lh,'receipt_sha256':sha(args.output)}))

if __name__=='__main__':main()
