"""Publish the freshly executed 261010 matrix, preserving prior report identity."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path('/wc1/holdouts/disturbed-wepp-261010-20261010/disturbed_matrix0')
PRIOR = Path('/wc1/holdouts/chrqin-disturbed-candidate-20261010/disturbed_matrix0')
OUT = HERE/'artifacts/release-261010'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    assert '99 passed' in Path('/tmp/wepp-261010-disturbed.log').read_text()
    old = json.loads((OUT/'previous-disturbed-report/analysis_results_current.provenance.json').read_text())
    expected = {p.name: sha(p) for p in (PRIOR/'output').iterdir() if p.is_file()}
    fresh = {p.name: sha(p) for p in (ROOT/'output').iterdir() if p.is_file()}
    assert len(fresh) == 768 and fresh == expected
    approved_changes = {'tests/disturbed/test_disturbed_matrix.py', 'tests/disturbed/analysis_context.md',
                        'wepp_runner/bin/wepp_261009_hill'}
    for name, digest in old['sources'].items():
        if name not in approved_changes:
            assert sha(REPO/name) == digest, name
    source_names = set(old['sources'])-{'wepp_runner/bin/wepp_261009_hill'}
    source_names.add('wepp_runner/bin/wepp_261010_hill')
    spec = importlib.util.spec_from_file_location('ranking_analysis', REPO/'tests/disturbed/analyze_matrix.py')
    analysis = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = analysis
    spec.loader.exec_module(analysis)
    events = analysis.load_all_events(ROOT/'output')
    peaks = analysis.load_all_peak_events(ROOT/'output')
    analysis.require_full_matrix(events, peaks)
    context = (REPO/'tests/disturbed/analysis_context.md').read_text()
    report = analysis.generate_full_report(analysis.analyze_all_comparisons(events, peaks), context=context)
    path = REPO/'tests/disturbed/analysis_results_current.md'
    path.write_text(report)
    cases = []
    shared = ['chan.inp', 'chntyp.txt', 'gwcoeff.txt', 'pmetpara.txt', 'snow.txt', 'wepp_ui.txt']
    for wid in range(1, 97):
        texture, severity, vegetation = analysis.wepp_id_to_params(wid)
        names = shared+[f'p{wid}.{ext}' for ext in ('run', 'cli', 'man', 'sol', 'slp')]
        cases.append(dict(id=wid, texture=texture, severity=severity, vegetation=vegetation,
                          inputs={n: sha(ROOT/'runs'/n) for n in names},
                          outputs={n: h for n, h in fresh.items() if n.startswith(f'H{wid}.')}))
    metadata = dict(date='2026-10-10', wepp_release='wepp_261010',
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        source_scope='Current publication freshness pins; execution used the explicit release-binary override below',
        executed_harness_sha256=old['sources']['tests/disturbed/test_disturbed_matrix.py'],
        execution_binary_override='/wc1/holdouts/wepp-261010-release-20261010/wepp_261010_hill',
        harness_change_after_execution='Only default binary literal changed from 261009 to 261010; explicit execution override was already 261010',
        forest_source_commit='7471bb5e981d14d0b8c1cdb88a16af305aed1b67',
        binary_sha256=sha(REPO/'wepp_runner/bin/wepp_261010_hill'), native_sha256=old['native_sha256'],
        sources={n: sha(REPO/n) for n in sorted(source_names)}, cases=cases,
        evidence_root=str(ROOT), fresh_cases=96, standard_output_files=768,
        byte_identical_to_validated_candidate=True, report_sha256=sha(path),
        previous_report_sha256=sha(OUT/'previous-disturbed-report/analysis_results_current.md.txt'))
    (REPO/'tests/disturbed/analysis_results_current.provenance.json').write_text(json.dumps(metadata, indent=2)+'\n')
    (OUT/'disturbed-release-parity.json').write_text(json.dumps(dict(
        fresh_cases=96, outputs_identical=768, release_outputs=fresh,
        binary_sha256=metadata['binary_sha256'], report_sha256=metadata['report_sha256']), indent=2)+'\n')
    print('Published fresh 261010 matrix: 96 cases, 768 outputs identical to validated candidate')


if __name__ == '__main__':
    main()
