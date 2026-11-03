"""Read-only independent preparation readback; writes one new review receipt."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import shlex
import sqlite3

from wepppy.soils.ssurgo import retention
from wepppy.wepp.soils.utils import WeppSoilUtil

ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/retention-preparation-v1')
ART = Path('/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts')
KEYS = {'53949', '1718465', '1718494', '1718510', '1856573', '2711184', '2711250'}
BASE_FIELDS = ('solthk', 'bd', 'ksat', 'anisotropy', 'fc', 'wp', 'sand', 'clay', 'orgmat', 'cec', 'rfg')
NATIVE_FIELDS = ('theta_r', 'theta_s', 'alpha', 'npar', 'ks', 'wp', 'fc')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def inventory(root):
    files = {}
    for path in root.rglob('*'):
        assert not path.is_symlink(), path
        if path.is_file():
            files[str(path)] = sha(path)
    return files


def semantic(path):
    """Cross-check every numeric horizon token against the installed parser."""
    obj = deepcopy(WeppSoilUtil(str(path), preserve_input_format=True).obj)
    del obj['header']
    lines = [line.strip() for line in Path(path).read_text().splitlines()
             if line.strip() and not line.lstrip().startswith('#')]
    version = int(lines[0])
    assert version in (7778, 9002) and obj['datver'] == version
    assert lines[1] == 'Any comments:'
    count, flag = map(int, lines[2].split())
    assert count == len(obj['ofes']) and flag == obj['ksflag']
    index = 3
    for ofe in obj['ofes']:
        if version == 9002:
            assert len(shlex.split(lines[index])) == 5
            index += 1
        descriptor = shlex.split(lines[index])
        assert len(descriptor) == 8
        assert int(descriptor[2]) == len(ofe['horizons'])
        index += 1
        for horizon in ofe['horizons']:
            tokens = list(map(float, lines[index].split()))
            assert len(tokens) == (18 if version == 9002 else 11)
            assert all(math.isfinite(value) for value in tokens)
            expected = {key: tokens[i] for i, key in enumerate(BASE_FIELDS)}
            if version == 9002:
                expected['native_hydraulics'] = dict(zip(NATIVE_FIELDS, tokens[11:], strict=True))
            assert expected == horizon, (path, index)
            index += 1
        assert len(lines[index].split()) == 3
        index += 1
    assert index == len(lines), (path, index, len(lines))
    return obj


def diff(a, b, path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        assert set(a) == set(b), path
        return [row for key in sorted(a) for row in diff(a[key], b[key], path + (key,))]
    if isinstance(a, list) and isinstance(b, list):
        assert len(a) == len(b), path
        return [row for i, (x, y) in enumerate(zip(a, b, strict=True))
                for row in diff(x, y, path + (i,))]
    return [] if a == b else [dict(path=list(path), before=a, after=b)]


def pair(a, b):
    rows = diff(a, b)
    for row in rows:
        p = row['path']
        assert len(p) == 5 and p[0] == 'ofes' and p[2] == 'horizons' and p[4] in ('fc', 'wp'), row
    return rows


def main():
    before = inventory(ROOT)
    declaration = read(ROOT / 'declaration.json')
    result = read(ROOT / 'preparation-result.json')
    expected_decl = '5be61161a62c428867735328cd9b085da64473e13d26d92f8b8aae88bb87da7b'
    assert sha(ROOT / 'declaration.json') == result['declaration_sha256'] == expected_decl
    assert result['passed'] is True and result['native_calls'] == result['network_requests'] == 0
    assert before == {**result['artifact_files'], str(ROOT / 'preparation-result.json'): sha(ROOT / 'preparation-result.json')}
    for bindings in (declaration['dependencies'], declaration['input_files'], declaration['cohort']['files']):
        for name, digest in bindings.items():
            assert sha(name) == digest, name
    assert sha(ROOT / 'source-cache.sqlite') == declaration['cohort']['cache_sha256']
    assert sha(ROOT / 'source-readback.json') == result['source_readback_sha256']
    assert sha(ROOT / 'case-readback.json') == result['case_readback_sha256']
    source_readback = read(ROOT / 'source-readback.json')
    case_readback = read(ROOT / 'case-readback.json')
    parsed = {str(p): semantic(p) for p in sorted(ROOT.rglob('*.sol'))}
    assert len(parsed) == 62
    proofs = {}
    for name in parsed:
        path = Path(name)
        relative = path.relative_to(ROOT)
        optional = 'optional' in relative.parts
        boundary = path.parent if relative.parts[0] == 'source-builds' else ROOT.joinpath(*relative.parts[:2])
        proof = retention.load_source_companion(path, provenance_root=boundary)
        assert (proof is not None) == optional, path
        if proof is not None:
            proofs[name] = proof
            for ofe in proof['lineage']:
                for row in ofe:
                    assert row['mukey'] in KEYS
                    assert row['source_receipt_sha256'] == declaration['cohort']['receipt_sha256']
    assert len(proofs) == 31
    joins = {(str(j['mukey']), str(j['chkey'])): j for j in source_readback['joins']}
    assert len(joins) == len(source_readback['joins']) == 37
    source_pairs, reasons = {}, Counter()
    with sqlite3.connect('file:' + declaration['cohort']['cache'] + '?mode=ro&immutable=1', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        for arm in ('default', 'optional'):
            assert {p.stem for p in (ROOT / 'source-builds' / arm).glob('*.sol')} == KEYS
        for key in sorted(KEYS):
            baseline = ROOT / 'source-builds/default' / (key + '.sol')
            candidate = ROOT / 'source-builds/optional' / (key + '.sol')
            changes = pair(parsed[str(baseline)], parsed[str(candidate)])
            assert changes == source_readback['paired_differences'][key]
            proof = proofs[str(candidate)]
            assert proof['mukey'] == key and proof['source_receipt_sha256'] == declaration['cohort']['receipt_sha256']
            component = conn.execute('SELECT * FROM component WHERE cokey=?', (proof['cokey'],)).fetchone()
            assert str(component['mukey']) == key
            decisions = {d['chkey']: d for d in proof['decisions']}
            for chkey, decision in decisions.items():
                original = dict(conn.execute('SELECT * FROM chorizon WHERE chkey=?', (chkey,)).fetchone())
                assert str(original['cokey']) == proof['cokey']
                assert all(value == original[field] for field, value in decision['source'].items())
                assert joins[key, chkey]['decision'] == decision
                assert joins[key, chkey]['source'] == decision['source']
                reasons[decision['reason']] += 1
                if decision['reason'] == 'eligible':
                    source = decision['source']
                    mass = decision['mass_percent'] / 100
                    share = 2.65 * (1 - mass) / (source['dbthirdbar_r'] * mass + 2.65 * (1 - mass))
                    for field, raw in [('fc', 'wthirdbar_r'), ('wp', 'wfifteenbar_r')]:
                        assert math.isclose(decision['inverse'][field], source[raw] / 100 / share, abs_tol=1e-14)
                else:
                    assert decision['prepared'] == decision['before']
            default_rows = parsed[str(baseline)]['ofes'][0]['horizons']
            optional_rows = parsed[str(candidate)]['ofes'][0]['horizons']
            for index, row in enumerate(proof['emitted_rows']):
                decision = decisions[row['chkey']]
                assert decision['emitted'] is True
                for field in ('fc', 'wp'):
                    assert default_rows[index][field] == round(decision['before'][field], 4)
                    assert optional_rows[index][field] == round(decision['prepared'][field], 4)
            source_pairs[key] = dict(changes=changes, rows=len(default_rows),
                                    source_decisions=len(decisions), component=proof['cokey'])
    cases = {}
    for label, case in declaration['cases'].items():
        material = case['case']['soil']
        relative = {'source': f'soils/{material}.sol', 'road': f'soils/{label}-road.sol',
                    'fill': f'soils/{label}-fill.sol', 'buffer': f'soils/{label}-buffer.sol',
                    'stack': f'soils/{label}-stack.sol', 'final': 'runs/p1.sol'}
        changes = {}
        for stage, name in relative.items():
            a, b = (ROOT / arm / label / name for arm in ('default', 'optional'))
            changes[stage] = pair(parsed[str(a)], parsed[str(b)])
            assert changes[stage] == case_readback['comparisons'][label]['paired_differences'][stage]
        for arm in ('default', 'optional'):
            copied = ROOT / arm / label / relative['source']
            source = ROOT / 'source-builds' / arm / (material + '.sol')
            assert sha(copied) == sha(source)
            if arm == 'optional':
                assert sha(str(copied) + '.retention.json') == sha(str(source) + '.retention.json')
            stage_obj = parsed[str(ROOT / arm / label / relative['final'])]
            assert [o['luse'] for o in stage_obj['ofes']] == ['bare', 'bare', 'forest']
            assert all(o['sat'] == 0.75 for o in stage_obj['ofes'])
        default, optional = (parsed[str(ROOT / arm / label / relative['final'])] for arm in ('default', 'optional'))
        frozen = semantic(case['frozen_soil'])
        drift = diff(frozen, default)
        assert drift == case_readback['comparisons'][label]['fresh_default_vs_frozen_u12']
        depths = lambda obj: [[h['solthk'] for h in o['horizons']] for o in obj['ofes']]
        assert depths(default) == depths(optional) == depths(frozen)
        deep = []
        for index, (a, b) in enumerate(zip(default['ofes'], optional['ofes'], strict=True)):
            x, y = a['horizons'][-1], b['horizons'][-1]
            deep.append(dict(ofe=index + 1, top_mm=a['horizons'][-2]['solthk'], bottom_mm=x['solthk'],
                             default={k: x[k] for k in ('fc', 'wp', 'bd', 'rfg', 'ksat')},
                             optional={k: y[k] for k in ('fc', 'wp', 'bd', 'rfg', 'ksat')}))
        if label in ('B2', 'B3'):
            assert all(r['top_mm'] == 990 and r['bottom_mm'] == 1600 for r in deep)
            assert all((r['default']['fc'], r['default']['wp'], r['optional']['fc'], r['optional']['wp'])
                       == (0.1851, 0.0823, 0.1751, 0.0778) for r in deep)
            assert {tuple(row['path']) for row in changes['final']} == {
                ('ofes', ofe, 'horizons', 7, field) for ofe in range(3) for field in ('fc', 'wp')}
        cases[label] = dict(paired_changes=changes, frozen_default_drift=drift,
                            horizon_depths_mm=depths(default), deep_rows=deep,
                            default_final_sha256=sha(ROOT / 'default' / label / 'runs/p1.sol'),
                            optional_final_sha256=sha(ROOT / 'optional' / label / 'runs/p1.sol'))
    assert [k for k, v in cases.items() if v['frozen_default_drift']] == ['B5']
    assert inventory(ROOT) == before
    for name, digest in declaration['cohort']['files'].items():
        assert sha(name) == digest
    output = dict(passed=True, gate='Actual preparation artifacts pass for the declared paired native pilot; B5 fresh-default drift must remain separate.',
                  reader_sha256=sha(__file__), declaration_sha256=expected_decl,
                  result_sha256=sha(ROOT / 'preparation-result.json'),
                  case_readback_sha256=sha(ROOT / 'case-readback.json'),
                  source_readback_sha256=sha(ROOT / 'source-readback.json'),
                  acquisition_sha256=declaration['cohort']['receipt_sha256'],
                  verified_files=before, parsed_soils=len(parsed), validated_companions=len(proofs),
                  native_9002_soils=sum(o['datver'] == 9002 for o in parsed.values()),
                  numeric_horizon_rows=sum(len(ofe['horizons']) for obj in parsed.values() for ofe in obj['ofes']),
                  joined_source_decisions=len(joins), decision_reasons=dict(reasons), source_pairs=source_pairs,
                  cases=cases, original_cohort_and_preparation_unchanged=True, native_calls=0, network_requests=0,
                  observation_limits='Uses installed parser/companion validator with independent raw numeric-token checks and independent comparison/cache joins. Does not rebuild sources or observe native outcomes.')
    destination = ART / 'resumption-r7-retention-preparation-outcome-readback.json'
    with destination.open('x') as stream:
        json.dump(output, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(passed=True, artifact=str(destination), sha256=sha(destination),
                         parsed_soils=len(parsed), companions=len(proofs),
                         numeric_horizon_rows=output['numeric_horizon_rows'], reasons=dict(reasons))))


if __name__ == '__main__':
    main()
