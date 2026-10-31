"""Independent exact hourly-return and source-free publication readback."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def real(value):
    return struct.unpack('f', struct.pack('f', value))[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--observer', type=Path, required=True)
    parser.add_argument('--publication', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest = read(args.publication / 'publication-manifest.json')
    for name, expected in manifest['files'].items():
        assert sha(args.publication / name) == expected
    for name, expected in manifest['raw_evidence_sha256'].items():
        assert sha(name) == expected
    summary = read(args.publication / 'summary-declaration.json')
    for name, expected in summary['input_sha256'].items():
        assert sha(name) == expected
    hourly = read(args.publication / 'hourly-return-reconciliation.json')
    expected = {(r['stratum'], r['lane'], r['day'], r['ofe']): r for r in hourly['rows']}
    tasks = read(args.observer / 'execution-declaration.json')['tasks']
    steps = additions = frames = 0
    for task in tasks:
        groups = defaultdict(lambda: defaultdict(list))
        trace = Path(task['folder']) / 'observations/buffer-observation.txt'
        assert sha(trace) == summary['input_sha256'][str(trace)]
        for line in trace.read_text().splitlines():
            fields = line.split()
            day, ofe, index = map(int, fields[2:5])
            if ofe:
                groups[(day, ofe)][fields[0]].append((index, list(map(float, fields[5:]))))
        for (day, ofe), tags in sorted(groups.items()):
            key = (task['stratum'], task['lane'], day, ofe)
            retained = expected[key]
            values = sorted(tags['BP_WBH_FLUX'])
            assert [index for index, _ in values] == list(range(1, 25))
            total = 0.0
            for _, vector in values:
                total = real(total + vector[0])
                assert total == vector[3]
                steps += 1
            assert total == retained['return_depth_local_m']
            rochek = tags['BP_ROCHEK_OUT']
            if rochek:
                assert len(rochek) == len(tags['BP_IRS_OUT']) == len(tags['BP_GEOMETRY']) == 1
                before = rochek[0][1][0]
                irs = tags['BP_IRS_OUT'][0][1]
                geometry = tags['BP_GEOMETRY'][0][1]
                result = real(before + real(real(total * geometry[1]) / irs[3]))
                assert result == irs[0]
                assert retained['rochek_to_irs_addition'] == {
                    'before_m': before, 'expected_m': result, 'observed_m': irs[0], 'exact': True}
                additions += 1
            else:
                assert retained['rochek_to_irs_addition'] is None
            frames += 1
    assert steps == 2592 and additions == 21 and frames == 108
    assert hourly['exact_REAL_hourly_additions'] == steps
    assert hourly['exact_rochek_to_irs_additions'] == additions
    result = {'passed': True, 'scope': 'Exact source-expression and publication integrity readback only; no native runs or whole-water-budget claim.',
              'published_files_rehashed': len(manifest['files']),
              'raw_evidence_files_rehashed': len(manifest['raw_evidence_sha256']),
              'hourly_REAL_accumulation_steps': steps,
              'rochek_to_irs_REAL_additions': additions, 'day_ofe_frames': frames,
              'evidence_sha256': {str(p): sha(p) for p in (
                  args.publication / 'publication-manifest.json',
                  args.publication / 'hourly-return-reconciliation.json',
                  args.publication / 'summary-declaration.json', Path(__file__).resolve())}}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'steps': steps, 'additions': additions, 'files': len(manifest['files'])}))


if __name__ == '__main__':
    main()
