"""Authored structural and semantic FH trace controls; no native invocation."""
import argparse
import json
from pathlib import Path
from read_history import read


def trace(stale_frozen=0, clearing=False, invalid_nw=False, mode=0, native_request=0):
    lines = ['FH_SCHEMA 1']
    sequence = 0
    nw = 0.00005 if clearing else (-0.00001 if invalid_nw else 0)
    def event(tag, rows):
        nonlocal sequence
        sequence += 1
        lines.append(f'E {tag} {sequence} 1 1 1 1 0 {mode} 1 0 0')
        lines.extend(row.format(seq=sequence) for row in rows)
    def snapshot(tag, after=False):
        water = 0 if after and clearing else nw
        frozen = 0 if after else stale_frozen
        event(tag, [f'C {{seq}} 1 1 1 0.1 0.05 0.04 0.02 0 {frozen} 0.025 0.02 {water} 0.25',
                    'F {seq} 1 1 0 0.25 0 0.1'])
    def branch(tag, values, i=1):
        event(tag, [f'B {{seq}} {i} 0 ' + ' '.join(map(str, values + [0] * (6 - len(values))))])
    snapshot('MAP_PRE')
    branch(f'D{mode}_START', [0], 0)
    branch(f'D{mode}_LAYER', [1])
    if mode == 0:
        branch('D0_CLEAR_PRE', [nw, 0, 0.02, 0.025])
        branch('D0_CLEAR_POST', [0 if clearing else nw, 0, 0.02, 0.025])
    else:
        branch('D1_REQUEST', [native_request])
    branch(f'D{mode}_FINISH', [0], 0)
    snapshot('MAP_POST', True)
    lines.append(f'FH_END {sequence} 1')
    return '\n'.join(lines) + '\n'


def main(out):
    out.mkdir(parents=True, exist_ok=False)
    def run(name, text):
        path = out / (name + '.txt')
        path.write_text(text)
        return read(path, out / (name + '-transfers.jsonl'))
    base = trace()
    valid = run('valid', base)
    assert valid['maps'] == 1
    assert abs(valid['signed_ranges']['direction_0_residual_m']['max']) < 1e-16
    coarse = next(line + '\n' for line in base.splitlines() if line.startswith('C 1 '))
    fine = 'F 1 1 1 0 0.25 0 0.1\n'
    variants = {
        'missing_footer': base.rsplit('FH_END', 1)[0],
        'missing_coarse': base.replace(coarse, ''),
        'missing_fine': base.replace(fine, ''),
        'duplicate_fine': base.replace(fine, fine * 2),
        'duplicate_coarse': base.replace(coarse, coarse * 2),
        'identity_drift': base.replace('E MAP_POST 7 1', 'E MAP_POST 7 2'),
        'sequence_gap': base.replace('E MAP_POST 7', 'E MAP_POST 8'),
        'invalid_clock': base.replace('1 1 1 0 0 1 0 0', '1 367 1 0 0 1 0 0'),
        'nonfinite': base.replace('0.25 0 0.1', 'NaN 0 0.1'),
        'parent_drift': base.replace('E MAP_POST 7 1 1 1 1 0 0 1 0 0', 'E MAP_POST 7 1 1 1 1 0 0 1 9 0'),
        'map_count': base.replace('FH_END 7 1', 'FH_END 7 2'),
        'trailing_data': base + 'V 7 0\n',
        'branch_clock': base.replace('E D0_LAYER 3 1 1 1 1 0 0 1 0 0', 'E D0_LAYER 3 1 1 1 1 1 0 1 0 0'),
        'branch_direction': base.replace('D0_LAYER', 'D1_LAYER'),
        'missing_finish': base.replace('D0_FINISH', 'D0_START'),
        'missing_branch_layer': base.replace('D0_LAYER', 'D0_START'),
    }
    results = []
    for name, value in variants.items():
        try:
            run(name, value)
        except ValueError as error:
            results.append(dict(case=name, rejected=True, reason=str(error)))
        else:
            raise AssertionError('Malformed evidence accepted: ' + name)
    unavailable = base.replace('C 1 1 1 1', 'C 1 1 0 0').replace('C 7 1 1 1', 'C 7 1 0 0')
    unavailable = '\n'.join(line for line in unavailable.splitlines() if not line.startswith('F ')) + '\n'
    result = run('unavailable', unavailable)
    assert result['counts']['unavailable_mapping_layers'] == 1 and not result['signed_ranges']
    gap = base.replace('B 4 1 0 0 0 0.02 0.025 0 0', 'G 4 1 0')
    result = run('branch_gap', gap)
    assert result['counts']['unavailable_branch_records'] == 1 and not result['signed_ranges']
    stale = run('stale_frozen_clear', trace(stale_frozen=0.02, clearing=True))
    assert stale['signature_counts']['H_frozen_liquid_clear'] == 1
    negative = run('negative_nw', trace(invalid_nw=True))
    assert negative['counts']['invalid_mapping_layers_excluded_from_signatures'] == 1
    assert not negative['signature_counts']
    native = run('native_request', trace(mode=1, native_request=1e-8))
    assert native['signed_ranges']['direction_1_residual_m']['min'] == -1e-8
    receipt = dict(passed=True, malformed_controls=results, unavailable_is_not_zero=True,
                   branch_gap_is_not_absence=True, stale_frozen_uses_actual_clear=True,
                   invalid_nw_excluded=True, native_request_observed=True)
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    main(parser.parse_args().out)
