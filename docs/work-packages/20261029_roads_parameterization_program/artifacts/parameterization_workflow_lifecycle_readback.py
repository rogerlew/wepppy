"""Read-only artifact checks after canonical Roads archive/reset/restore/fork.

Run with wctl run-python. Only evidence receipts are written; no controller
post-load hooks, run mutation, native execution, extraction or copy is performed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import zipfile

from parameterization_workflow import RAW, RUN, SOURCE, inventory
from wepppy.nodb.mods.roads.roads import Roads
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

CHECKPOINT = RAW / 'lifecycle-custom-checkpoint-v1.json'
FIELDS = {'ki_kg_s_m4': 5, 'kr_s_m': 6, 'critical_shear_pa': 7, 'ksat_mm_h': 8}
ROLES = {'Road': 'road', 'Fill': 'fill', 'Forest': 'buffer'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_hash(data):
    return digest(json.dumps(data, sort_keys=True, separators=(',', ':')).encode())


def decode(text):
    controller = Roads._decode_jsonpickle(Roads._preprocess_json_for_decode(text))
    assert isinstance(controller, Roads)
    return controller.__dict__


def preserved(root):
    source = json.loads((RAW / 'preparation-declaration.json').read_text())['source_inventory']
    baseline = json.loads((RAW / 'baseline-before.json').read_text())
    assert inventory(SOURCE) == source, 'Source study inventory changed'
    assert inventory(root, ('wepp/runs', 'wepp/output')) == baseline, 'Protected baseline changed'
    return {'source_preserved': True, 'baseline_preserved': True,
            'source_file_count': len(source), 'baseline_file_count': len(baseline)}


def completed(root):
    state = decode((root / 'roads.nodb').read_text())
    parameterization = state['_parameterization']
    config_hash = canonical_hash(parameterization)
    baseline = parameterization['baseline']
    assert len(baseline['assets']) == 18
    for name, asset in baseline['assets'].items():
        assert digest(asset['text'].encode()) == asset['sha256'], name
    receipt = lifecycle.require_current(root)
    assert receipt['parameterization_hash'] == config_hash
    snapshot_path = root / lifecycle.PARAMETERIZATION_SNAPSHOT
    assert receipt['parameterization_snapshot_sha256'] == digest(snapshot_path.read_bytes())
    manifest_path = root / 'wepp/roads/segments/roads.segment.pass.manifest.json'
    manifest = json.loads(manifest_path.read_text())
    rows = [row for row in manifest if row['status'] == 'completed']
    assert len(rows) == 35 and not any(row['status'] == 'failed' for row in manifest)
    inputs, native = {}, []
    for row in rows:
        provenance = row['parameterization']
        assert provenance['configuration_hash'] == config_hash
        assert provenance['baseline_id'] == baseline['id']
        paths = {}
        for entry in provenance['input_files']:
            relative = entry['relpath']
            path = root / relative
            assert path.resolve().is_relative_to(root.resolve())
            actual_hash = digest(path.read_bytes())
            assert actual_hash == entry['sha256'], relative
            inputs[relative] = actual_hash
            paths[path.suffix] = path
        assert set(paths) == {'.sol', '.slp', '.man'}
        tokens = [shlex.split(line) for line in paths['.sol'].read_text().splitlines()
                  if line.lstrip().startswith("'")]
        assert len(tokens) == len(provenance['ofes']) == 3
        for fields, ofe in zip(tokens, provenance['ofes']):
            role = ROLES[fields[0]]
            assert role == ofe['role']
            values = {key: float(fields[index]) for key, index in FIELDS.items()}
            assert values == ofe['emitted']
            native.append({'segment_run_id': row['segment_run_id'], 'role': role, 'values': values})
    return {
        'parameterization': parameterization, 'roads_params': state['_roads_params'],
        'configuration_hash': config_hash, 'current_receipt': receipt,
        'native_values': native, 'input_hashes': inputs,
        # Include ordinary current and historical Roads artifacts, excluding only
        # mutable .log files as in the established source inventory convention.
        'roads_artifact_hashes': inventory(root, ('wepp/roads',)),
        'protected_baseline_hashes': inventory(root, ('wepp/runs', 'wepp/output')),
    }


def main(action, label):
    output = CHECKPOINT if action == 'snapshot' else RAW / f'lifecycle-{action}-{label}.json'
    if output.exists():
        raise FileExistsError(output)
    root = RUN.with_name(RUN.name + '-fork') if action == 'fork' else RUN
    result = {'action': action, 'label': label, 'root': str(root),
              'at': datetime.now(timezone.utc).isoformat(),
              'helper_sha256': digest(Path(__file__).read_bytes())}
    result.update(preserved(root))
    if action == 'snapshot':
        data = completed(root)
        assert all(entry == {'mode': 'multiply', 'value': 2}
                   for role in data['parameterization']['overrides'].values()
                   for entry in role.values())
        native = json.loads((RAW / 'native-custom-restarted-readback.json').read_text())
        assert native['configuration_hash'] == data['configuration_hash']
        assert native['input_hashes'] == data['input_hashes']
        assert native['native_values'] == data['native_values']
        result.update(data)
    else:
        checkpoint = json.loads(CHECKPOINT.read_text())
        result['checkpoint_sha256'] = digest(CHECKPOINT.read_bytes())
        if action == 'archive':
            browser = json.loads((RAW / 'archive.json').read_text())
            assert browser['passed'] and browser['job']['final']['status'] == 'finished'
            archive = RUN / 'archives' / browser['archive_name']
            assert archive.resolve().is_relative_to((RUN / 'archives').resolve())
            expected = {**checkpoint['roads_artifact_hashes'], **checkpoint['protected_baseline_hashes']}
            with zipfile.ZipFile(archive) as zf:
                assert zf.testzip() is None
                state = decode(zf.read('roads.nodb').decode())
                assert state['_parameterization'] == checkpoint['parameterization']
                assert state['_roads_params'] == checkpoint['roads_params']
                for relative, expected_hash in expected.items():
                    assert digest(zf.read(relative)) == expected_hash, relative
                result.update(archive_name=archive.name, archive_sha256=digest(archive.read_bytes()),
                              verified_member_count=len(expected) + 1,
                              retained_parameterization_exact=True, generated_artifacts_exact=True)
        elif action == 'reset':
            state = decode((root / 'roads.nodb').read_text())
            parameterization = state['_parameterization']
            assert parameterization['baseline'] == checkpoint['parameterization']['baseline']
            assert all(entry == {'mode': 'default'}
                       for role in parameterization['overrides'].values() for entry in role.values())
            assert state['_roads_params'] == checkpoint['roads_params']
            try:
                lifecycle.require_current(root)
            except lifecycle.RoadsResultsUnavailable as exc:
                result['current_rejection'] = str(exc)
            else:
                raise AssertionError('Reset result remained eligible')
            histories = list((root / lifecycle.HISTORY).glob('*/wepp/roads/output/roads.current.json'))
            matched = [str(path.relative_to(root)) for path in histories
                       if json.loads(path.read_text()) == checkpoint['current_receipt']]
            assert matched, 'Custom completed publication history missing after Reset'
            result.update(retained_baseline_exact=True, all_overrides_default=True,
                          historical_custom_receipts=matched, current_eligible=False)
        else:
            data = completed(root)
            for key in ('parameterization', 'roads_params', 'configuration_hash', 'current_receipt',
                        'native_values', 'input_hashes', 'roads_artifact_hashes', 'protected_baseline_hashes'):
                assert data[key] == checkpoint[key], key
            result.update(configuration_hash=data['configuration_hash'],
                          retained_parameterization_exact=True, native_values_exact=True,
                          input_file_count=len(data['input_hashes']),
                          roads_artifact_count=len(data['roads_artifact_hashes']),
                          current_eligible=True, current_receipt=data['current_receipt'])
    result['passed'] = True
    with output.open('x') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(action, 'passed:', output.name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['snapshot', 'archive', 'reset', 'restored', 'fork'])
    parser.add_argument('--label', default='v1')
    args = parser.parse_args()
    main(args.action, args.label)
