"""Read-only checkpoint closure review; never executes a native model."""
from pathlib import Path
import argparse,hashlib,json,tarfile

REPO=Path('/workdir/wepppy').resolve()
ART=REPO/'docs/work-packages/20261029_roads_parameterization_program/artifacts'
RAW=REPO/'out/roads-parameterization-program-20261031'

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def archive_check(receipt_name,roots):
    receipt=read(ART/receipt_name);archive=Path(receipt['archive'])
    assert archive.stat().st_size==receipt['bytes'] and sha(archive)==receipt['sha256']
    manifest_path=Path(str(archive)+'.manifest.json')
    assert sha(manifest_path)==receipt['manifest_sha256']
    manifest=read(manifest_path);assert len(manifest)==receipt['files']
    assert read(Path(str(archive)+'.aliases.json'))==receipt['omitted_aliases']=={}
    actual={str(p.relative_to(RAW)):sha(p) for root in roots for p in (RAW/root).rglob('*') if p.is_file()}
    assert actual==manifest,('raw tree closure differs',set(actual)^set(manifest))
    seen={};size=0
    with tarfile.open(archive,'r|gz') as stream:
        for member in stream:
            assert member.isfile() and member.name not in seen
            assert not member.name.startswith('/') and '..' not in Path(member.name).parts
            source=stream.extractfile(member);assert source is not None
            seen[member.name]=hashlib.file_digest(source,'sha256').hexdigest();size+=member.size
    assert seen==manifest and size==receipt['uncompressed_bytes']
    assert sha(archive)==receipt['sha256']
    return dict(receipt=receipt_name,receipt_sha256=sha(ART/receipt_name),archive_sha256=receipt['sha256'],manifest_sha256=receipt['manifest_sha256'],files=len(seen),uncompressed_bytes=size,exact_archive_member_set=True,all_member_bytes_rehashed=True,raw_tree_matches_full_manifest=True,roots=roots)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    assert not args.output.exists()
    ledger_path=ART/'candidate-ledger-v19.json';ledger=read(ledger_path)
    ledger_hash=sha(ledger_path)
    assert ledger['version']==19 and ledger['status']=='no_parameter_candidate_accepted'
    assert not ledger['production_defaults_changed'] and ledger['withheld_materials_untouched'] and ledger['ui_specification_and_layout_human_gate_preserved']
    assert sha(ART/ledger['predecessor']['path'])==ledger['predecessor']['sha256']
    for name,digest in ledger['evidence_sha256'].items():assert sha(ART/name)==digest,name
    failed=ledger['roughness_persistence_isolation'];accepted=ledger['roughness_coupling_localization']
    assert (failed['initial_coverage_attempt_native_runs'],failed['corrected_preflight_native_runs'],failed['remaining_runs_not_executed'])==(1,4,32)
    assert not failed['modern_upstream_isolation_pass'] and failed['no_retrospective_acceptance']
    assert (accepted['full_period_replays'],accepted['unique_mode_histories'],accepted['years_per_run'],accepted['ordinary_outputs_exact'],accepted['full_state_traces_exact'])==(4,2,16,28,4)
    assert (accepted['state_rows_reviewed'],accepted['bounded_rows_reviewed'])==(583264,22268)
    assert not any(accepted[k] for k in ('qinf_nonlinear_law_independently_solved','physical_routing_validated','roughness_100mm_physically_validated','new_native_defect_established','parameter_candidate_accepted'))
    pub=read(ART/'buffer-roughness-coupling-localization-r4-publication-review.json')
    assert pub['accepted_publication'] and not pub['blocking_findings']
    for row in pub['public_allowlist']:assert sha(REPO/row['path'])==row['sha256'],row['path']
    packet=ART/'buffer-roughness-coupling-localization-r4';manifest=read(packet/'manifest.json')
    assert sha(packet/'manifest.json')==pub['packet_manifest_sha256']
    assert {p.name for p in packet.iterdir() if p.is_file()}==set(manifest['files'])|{'manifest.json'}
    for name,digest in manifest['files'].items():assert sha(packet/name)==digest
    science=read(ART/'buffer-roughness-coupling-localization-r4-publication-scientific-review.json')
    assert science['accepted_publication_claims'] and science['packet_manifest_sha256']==pub['packet_manifest_sha256']
    for path,digest in science['bindings'].items():assert sha(path)==digest,path
    docs=[REPO/'PROJECT_TRACKER.md',ART.parent/'package.md',ART.parent/'tracker.md',ART.parent/'prompts/active/program_execplan.md']
    for path in docs:
        text=path.read_text();assert 'whole-hillslope' in text and '32' in text and '28' in text
    assert 'awaiting direct observation' not in docs[-1].read_text()
    archives=[archive_check('revision4-buffer-roughness-counterfactual-retention.json',['buffer-roughness-counterfactual-r4']),archive_check('revision4-buffer-roughness-coupling-localization-retention.json',['buffer-roughness-coupling-localization-r4','buffer-roughness-coupling-interpretation-r4'])]
    assert [x['files'] for x in archives]==[4564,1409]
    assert sha(ledger_path)==ledger_hash
    extra=[ledger_path,ART/'revision4-buffer-roughness-coupling-localization-retention.json',ART/'buffer-roughness-coupling-localization-r4-publication-review.json',ART/'buffer-roughness-coupling-localization-r4-publication-scientific-review.json',Path(__file__).resolve(),*docs]
    report=dict(review='Independent exact checkpoint and archive closure addendum',accepted_checkpoint=True,blocking_findings=[],ledger_sha256=ledger_hash,evidence_hashes_verified=len(ledger['evidence_sha256']),public_allowlist_files_rehashed=len(pub['public_allowlist']),packet_manifest_sha256=pub['packet_manifest_sha256'],archives=archives,total_archive_members_verified=sum(x['files'] for x in archives),living_documents_reviewed=[str(p.relative_to(REPO)) for p in docs],scope='Completed failed-isolation and accepted observation-only localization checkpoint. New36-run study is separate and is not accepted by this receipt.',remaining_limits=['Original upstream-isolation campaign remains failed.','No parameter/default/binary change or physical-routing validation is accepted.','New study design, executable runner and fresh execution declaration require their own review.'],additional_public_allowlist=[dict(path=str(p.relative_to(REPO)),sha256=sha(p)) for p in extra],writer_clear=True,native_model_runs_by_reviewer=0)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'accepted_checkpoint':True,'archives':len(archives),'members':report['total_archive_members_verified'],'ledger_sha256':ledger_hash,'receipt_sha256':sha(args.output)}))

if __name__=='__main__':main()
