"""Bind the approved r7 PDF and final validation receipts before public delivery."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

WEPPPY = Path('/home/workdir/wepppy')
NATIVE = Path('/home/workdir/wepp-forest-release-20261009')
EVIDENCE = Path('/wc1/holdouts/mipa-native-r7-20261103')
REPORT = NATIVE / 'docs/release-notes/wepp_261029'
ARTIFACTS = WEPPPY / 'docs/work-packages/20261102_mofe_input_producer_audit/artifacts'
PDF_HASH = '0cdd7c74ac7c2277a144e27d9a8053578eb6e63b6819b857bd45691b9fe69b3c'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    published = WEPPPY / 'wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029/publication-manifest-r7.json'
    assert not published.exists(), 'Revision 7 is already published; preserve its frozen evidence and use a new revision'
    log = (EVIDENCE / 'wepppy-broad-continuation-v3.log').read_text()
    terminal = [line for line in log.splitlines() if re.match(r'^=+ .*passed.* in .* =+$', line)]
    assert terminal and 'failed' not in terminal[-1] and 'error' not in terminal[-1], 'Broad continuation must complete successfully first'
    broad = {'first_segment': '1 failed, 6440 passed, 182 skipped; obsolete prep-service test double repaired',
             'fixture_module_rerun': '3 passed',
             'second_segment': '1 failed, 6138 passed, 242 skipped, 6622 deselected; catalog compare returned busy under its database-wide advisory lock',
             'catalog_rerun': '24 passed without code changes',
             'continuation_command': 'wctl run-pytest tests --maxfail=1 -p docs.work-packages.20261102_mofe_input_producer_audit.artifacts.resume_mipa03_pytest_v3',
             'continuation_summary': terminal[-1].strip('= '),
             'uninterrupted_full_suite_pass': False,
             'counts_overlap_do_not_sum': True}
    metadata = {name: json.loads((NATIVE / 'release' / (name + '.json')).read_text())
                for name in ('wepp_261029', 'wepp_261029_hill')}
    source = metadata['wepp_261029']['source_commit']
    for name, sidecar in metadata.items():
        assert sidecar['source_commit'] == source
        assert digest(NATIVE / 'release' / name) == sidecar['sha256']
        for suffix in ('', '.json'):
            assert (NATIVE / 'release' / (name + suffix)).read_bytes() == (WEPPPY / 'wepp_runner/bin' / (name + suffix)).read_bytes()
    assert digest(REPORT / 'build-r7/main-r7.pdf') == PDF_HASH
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', source, 'src', 'fpm-src'], cwd=NATIVE, text=True).splitlines()
    sources = {}
    for name in paths:
        path = Path(name)
        if path.suffix.lower() not in ('.for', '.f90', '.inc', '.c', '.h') and path.name != 'makefile':
            continue
        blob = subprocess.check_output(['git', 'show', f'{source}:{name}'], cwd=NATIVE)
        assert (NATIVE / name).read_bytes() == blob, f'Uncommitted source drift: {name}'
        sources[name] = hashlib.sha256(blob).hexdigest()
    freeze = {'source_commit': source, 'source_files': sources,
              'authoring': {name: digest(REPORT / name) for name in ('main-r7.tex', 'release-identities-r7.tex', 'REVISION-7.md')},
              'pdf_sha256': PDF_HASH}
    write_json(REPORT / 'evidence/source-freeze-r7.json', freeze)
    evidence_paths = set(EVIDENCE.glob('*.log')) | set(EVIDENCE.glob('*.json'))
    # Bind retained attempts, successful receipts and independent reviews without copying private data.
    for directory in ('baseline-r6', 'configured-execution-v1', 'configured-observation-v2',
                      'configured-independent-qa', 'mode-history-final-qa', 'final-pdf-qa',
                      'security-workflow-v1', 'security-implementation-v1', 'security-implementation-v2',
                      'growth-qa', 'hydraulic-residue-qa', 'mode-history-qa'):
        evidence_paths.update((EVIDENCE / directory).glob('*.json'))
        evidence_paths.update((EVIDENCE / directory).glob('*.log'))
    for name in metadata['wepp_261029']['validation_evidence']:
        evidence_paths.add(EVIDENCE / name)
    evidence_paths.update(ARTIFACTS.glob('mipa03_*.md'))
    evidence_paths.update(REPORT.glob('build-r7/compile*.log'))
    register = {'source_commit': source,
                'scope': 'Local undeployed reference compatibility; retained failed attempts are historical, final receipts govern acceptance.',
                'broad_python': broad,
                'evidence': {str(path): {'sha256': digest(path)} for path in sorted(evidence_paths) if path.is_file()}}
    write_json(REPORT / 'evidence-register-r7.json', register)
    reviews = {key: digest(ARTIFACTS / name) for key, name in {
        'implementation_correctness': 'mipa03_implementation_review.md',
        'implementation_security': 'mipa03_implementation_security.md',
        'configured_artifacts_qa': 'mipa03_configured_artifact_qa.md',
        'pdf_correctness': 'mipa03_final_pdf_correctness.md',
        'pdf_visual_qa': 'mipa03_final_pdf_qa.md'}.items()}
    manifest = {
        'schema': 'wepp-release-notes-v1', 'release_tag': '261029',
        'artifact_revision': 7, 'document_revision': 7, 'document_date': '2026-11-02',
        'publication_status': 'local undeployed compatibility revision',
        'approval_record': 'Operator authorized local revision and publication; exact PDF approved by independent technical/visual AI reviews. Final provenance and publication reviews are retained separately.',
        'pdf_filename': 'wepp_261029_release-notes-r7.pdf', 'pdf_sha256': PDF_HASH,
        'public_path': '/weppcloud/static/reports/wepp/release-notes/wepp_261029/wepp_261029_release-notes-r7.pdf',
        'pages': 4, 'figures': 0, 'model_source_identity': source,
        'model_port_commit': '0d99afdfe',
        'source_comparison_baseline': metadata['wepp_261029']['supersedes']['source_commit'],
        'specialized_reference': metadata['wepp_261029']['specialized_reference'],
        'binary_sha256': {name: value['sha256'] for name, value in metadata.items()},
        'sidecar_sha256': {name: digest(NATIVE / 'release' / (name + '.json')) for name in metadata},
        'known_limitations': metadata['wepp_261029']['known_limitations'],
        'completed_actual_byte_gates': {
            'native_tests': 1750, 'subsequent_producer_reader_cases': 2,
            'focused_reader_module_total_overlaps_full_suite': 27,
            'compiled_reference_candidate_checks_overlaps_full_suite': 295,
            'mode_checks_overlaps_full_suite': 10, 'hillslope_watchlist': 31,
            'native_host_smokes': 2, 'post_vendor_host_smokes': 2, 'post_vendor_tests': 8,
            'specialized_16_year_histories': 8, 'water_rows_per_history': 17532,
            'no_RAP_9005_histories': 4, 'exact_revision6_control_cases': 6,
            'actual_project_hills': 72, 'actual_project_ofes': 235,
            'actual_project_calendar_years': 35, 'actual_project_outputs': 576,
            'actual_project_unique_finite_water_rows': 3004240,
            'configured_native_cover_values': 2940, 'configured_native_soil_headers': 14,
            'configured_observer_exact_output_files': 24,
            'installed_report_readback': True, 'installed_pair_application': True,
            'original_project_unchanged_file_hashes': 1536,
            'focused_python_tests': 75, 'browse_evidence_test': 1,
            'python_broad_segmented': broad,
        },
        'review_receipts': reviews,
        'source_freeze_sha256': digest(REPORT / 'evidence/source-freeze-r7.json'),
        'evidence_register_sha256': digest(REPORT / 'evidence-register-r7.json'),
        'preserve_issued_earlier_pdfs': True,
        'public_attachments': ['wepp_261029_release-notes-r7.pdf', 'publication-manifest-r7.json'],
        'legacy_source_attached': False, 'deployment': False,
    }
    write_json(REPORT / 'publication-manifest-r7.json', manifest)
    write_json(ARTIFACTS / 'mipa03_release_evidence.json', {
        'source_commit': source, 'binary_sha256': manifest['binary_sha256'],
        'pdf_sha256': PDF_HASH, 'private_evidence_root': str(EVIDENCE),
        'broad_python': broad,
        'evidence_register': str(REPORT / 'evidence-register-r7.json'),
        'evidence_register_sha256': manifest['evidence_register_sha256'],
        'source_freeze_sha256': manifest['source_freeze_sha256'],
        'validation': manifest['completed_actual_byte_gates'],
        'known_limitations': manifest['known_limitations'],
    })
    print(json.dumps(broad, indent=2))


if __name__ == '__main__':
    main()
