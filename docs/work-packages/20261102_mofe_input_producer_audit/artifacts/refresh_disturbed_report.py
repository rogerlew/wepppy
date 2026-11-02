"""Refresh current benchmark only after all fresh output hashes match history."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import subprocess
import wepppyo3.wepp_interchange.wepp_interchange_rust as native

REPO = Path('/workdir/wepppy')
EVIDENCE = REPO / 'docs/work-packages/20261102_mofe_input_producer_audit/artifacts'
MATRIX = Path('/wc1/holdouts/mipa-disturbed-producer-20261102/disturbed_matrix0')
PROVENANCE = Path('tests/disturbed/analysis_results_current.provenance.json')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old = json.loads(subprocess.check_output(['git', 'show', '4579b11ce:' + str(PROVENANCE)], cwd=REPO))
    assert os.environ.get('WEPP_DISTURBED_BINARY', 'wepp_261010') == 'wepp_261010'
    assert sha(REPO / 'wepp_runner/bin/wepp_261010_hill') == old['binary_sha256']
    current = deepcopy(old)
    changed_inputs = []
    changed_outputs = []
    for before, case in zip(old['cases'], current['cases']):
        for section, directory in [('inputs', 'runs'), ('outputs', 'output')]:
            for name, previous in before[section].items():
                digest = sha(MATRIX / directory / name)
                case[section][name] = digest
                if digest != previous:
                    (changed_inputs if section == 'inputs' else changed_outputs).append({'case': case['id'], 'file': name, 'old': previous, 'new': digest})
    comparison = {'cases': len(current['cases']), 'output_files': sum(len(c['outputs']) for c in current['cases']),
                  'changed_inputs': changed_inputs, 'changed_outputs': changed_outputs,
                  'previous_report_sha256': old['report_sha256'], 'matrix_root': str(MATRIX)}
    (EVIDENCE / 'disturbed_matrix_comparison.json').write_text(json.dumps(comparison, indent=2)+'\n')
    assert not changed_outputs, 'Fresh outputs differ; review numerical context before publication'
    context_path = REPO / 'tests/disturbed/analysis_context.md'
    context = context_path.read_text().replace('Reviewed: **2026-10-10**.', 'Reviewed: **2026-11-02**.')
    context = context.replace('Standard outputs match the validated candidate matrix byte-for-byte.',
        'After the MOFE producer repairs, all 768 standard outputs again match the\n2026-10-10 validated matrix byte-for-byte. These single-OFE controls do not\nestablish heterogeneous MOFE native correctness; its capacity, PMET adapter and\nFC/HK ownership acceptance remains on hold.')
    context_path.write_text(context)
    subprocess.run(['python', 'tests/disturbed/analyze_matrix.py', '--output-dir', str(MATRIX/'output'),
                    '--context', 'tests/disturbed/analysis_context.md', '--out', 'tests/disturbed/analysis_results_current.md'], cwd=REPO, check=True,
                   stdout=(EVIDENCE/'disturbed_report_analyzer.log').open('w'))
    current.update(date='2026-11-02', source_commit='4579b11cebd17e59b6cab486bcf699f9474fb9c6',
        source_scope='Fresh execution of working tree based on the contract ancestor; exact source hashes below bind reviewed producer code.',
        evidence_root=str(MATRIX), previous_report_sha256=old['report_sha256'],
        report_sha256=sha(REPO/'tests/disturbed/analysis_results_current.md'),
        native_sha256=sha(Path(native.__file__)), execution_binary_override=None,
        harness_change_after_execution='None; default wepp_261010 hillslope binary used.',
        executed_harness_sha256=sha(REPO/'tests/disturbed/test_disturbed_matrix.py'))
    sources = set(old['sources']) | {'wepppy/wepp/soils/utils/wepp_soil_util.py',
        'wepppy/wepp/soils/horizon_boundary.py', 'wepppy/wepp/soils/utils/utils.py'}
    current['sources'] = {name: sha(REPO/name) for name in sorted(sources)}
    (REPO/PROVENANCE).write_text(json.dumps(current, indent=2)+'\n')
    print(json.dumps({'fresh_cases': len(current['cases']), 'outputs_equal': comparison['output_files'],
                      'changed_input_files': len(changed_inputs), 'report_sha256': current['report_sha256']}))


if __name__ == '__main__':
    main()
