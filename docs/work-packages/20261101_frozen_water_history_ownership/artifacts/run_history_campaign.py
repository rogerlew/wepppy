"""Execute a frozen observational declaration; retain every bounded attempt."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from read_history import read, sha

REPO = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RAW = REPO / 'out/frozen-water-history-20261101'
OLD = REPO / 'out/sift-rock-frozen-water-20261101'
PREVIOUS = REPO / 'docs/work-packages/20261101_sift_rock_frozen_water/artifacts'
PROBE = REPO / 'out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/native-probe'
PINNED = '5f6bcebac1c82111a6a7c9685cd0d2a04f2e6c3066a3637e533a1a8054ff38b1'
ENV = {**os.environ, 'PATH': '/usr/bin:/bin', 'FC': '/usr/bin/gfortran'}


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def inventory(root):
    return {str(p.relative_to(root)): dict(sha256=sha(p), bytes=p.stat().st_size,
                                          mtime_ns=p.stat().st_mtime_ns)
            for p in sorted(root.rglob('*')) if p.is_file()}


def check(root, records, timestamps=True):
    actual = inventory(root)
    if not timestamps:
        actual = {k: v['sha256'] for k, v in actual.items()}
        records = {k: v['sha256'] for k, v in records.items()}
    if actual != records:
        raise ValueError('Inventory drift: ' + str(root))


def execute(command, cwd, stem, timeout, stdin=None):
    receipt = dict(command=list(map(str, command)), cwd=str(cwd), timeout_seconds=timeout,
                   PATH=ENV['PATH'], FC=ENV['FC'], started=time.time())
    with (cwd / (stem + '.stdout')).open('xb') as stdout, (cwd / (stem + '.stderr')).open('xb') as stderr:
        source = stdin.open('rb') if stdin else subprocess.DEVNULL
        try:
            result = subprocess.run(receipt['command'], cwd=cwd, env=ENV, stdin=source,
                                    stdout=stdout, stderr=stderr, timeout=timeout)
            receipt.update(status='completed', returncode=result.returncode)
        except subprocess.TimeoutExpired:
            receipt.update(status='timeout', returncode=None)
        finally:
            if stdin:
                source.close()
    receipt.update(elapsed_seconds=time.time() - receipt['started'],
                   stdout_sha256=sha(cwd / (stem + '.stdout')),
                   stderr_sha256=sha(cwd / (stem + '.stderr')))
    save(cwd / (stem + '-result.json'), receipt)
    return receipt


def freeze():
    prepared = RAW / 'prepared-v8'
    old_build = json.loads((PROBE / 'build-receipt.json').read_text())
    check(PROBE / 'build', old_build['inventory'])
    if sha(PROBE / 'build/src/wepp') != PINNED:
        raise ValueError('Pinned binary drift')
    tool_paths = ['/usr/bin/gfortran', '/usr/bin/make', '/usr/bin/gcc', '/usr/bin/as', '/usr/bin/ld']
    for name in ['f951', 'collect2']:
        p = subprocess.check_output(['/usr/bin/gfortran', '-print-prog-name=' + name], env=ENV, text=True).strip()
        tool_paths.append(str(Path(p).resolve()))
    tools = {p: sha(Path(p)) for p in tool_paths}
    libraries = old_build['runtime']['sha256']
    for p, expected in libraries.items():
        if sha(Path(p)) != expected:
            raise ValueError('Runtime library drift: ' + p)
    bindings = json.loads((prepared / 'source-bindings.json').read_text())
    for name, record in bindings.items():
        if sha(PROBE / 'build/src' / name) != record['before'] or sha(prepared / name) != record['after']:
            raise ValueError('Prepared source drift')
    files = ['fh_state.inc', 'fh_observer.for', 'observer_control_driver.for',
             'read_history.py', 'run_history_campaign.py', 'history-declaration.md',
             'check_history_reader.py']
    result = dict(schema=1, prepared=inventory(prepared), base_build=old_build['inventory'],
                  tools=tools, libraries=libraries, public={n: sha(HERE / n) for n in files},
                  prior_sift=inventory(OLD / 'sift-native-v1'),
                  prior_controls=inventory(OLD / 'frozen-campaign-v1'),
                  prior_readback_sha256=sha(OLD / 'sift-readback-v2/receipt.json'),
                  previous_public={n: sha(PREVIOUS / n) for n in
                      ['frozen-cases.json', 'frozen-design-source-bindings.json', 'run_frozen_campaign.py']},
                  invocation_budget=dict(synthetic=29, full_baseline=6, full_observer=6))
    save(RAW / 'freeze.json', result)
    print('Frozen declaration; no model invocation', flush=True)


def verify(frozen):
    for name, expected in frozen['public'].items():
        if sha(HERE / name) != expected:
            raise ValueError('Public execution dependency drift: ' + name)
    for name, expected in frozen['previous_public'].items():
        if sha(PREVIOUS / name) != expected:
            raise ValueError('Previous declaration drift: ' + name)
    for path, expected in {**frozen['tools'], **frozen['libraries']}.items():
        if sha(Path(path)) != expected:
            raise ValueError('Tool/runtime drift: ' + path)
    check(RAW / 'prepared-v8', frozen['prepared'])
    check(PROBE / 'build', frozen['base_build'])
    check(OLD / 'sift-native-v1', frozen['prior_sift'])
    check(OLD / 'frozen-campaign-v1', frozen['prior_controls'])
    if sha(OLD / 'sift-readback-v2/receipt.json') != frozen['prior_readback_sha256']:
        raise ValueError('Prior accepted readback drift')


def build(root):
    target = root / 'build'
    shutil.copytree(PROBE / 'build', target, copy_function=shutil.copy2)
    prepared = RAW / 'prepared-v8'
    for path in prepared.glob('*.for'):
        shutil.copyfile(path, target / 'src' / path.name)
    shutil.copyfile(prepared / 'fh_state.inc', target / 'src/fh_state.inc')
    before = inventory(target)
    result = execute(['/usr/bin/make', '-j4', 'FC=/usr/bin/gfortran', 'LINKER=/usr/bin/gfortran', 'wepp'],
                     target / 'src', 'observer-build', 300)
    save(root / 'build-receipt.json', dict(result=result, before=before, after=inventory(target)))
    if result['returncode'] != 0:
        raise RuntimeError('Observer build failed; evidence retained')
    return target / 'src/wepp'


def controls(root):
    base = OLD / 'frozen-campaign-v1'
    target = root / 'controls'
    target.mkdir()
    build_dir = target / 'build'
    build_dir.mkdir()
    bindings = json.loads((PREVIOUS / 'frozen-design-source-bindings.json').read_text())['files']
    for name, record in bindings.items():
        source = base / 'build' / name
        if sha(source) != record['sha256']:
            raise ValueError('Synthetic source drift')
        shutil.copyfile(source, build_dir / name)
    shutil.copyfile(RAW / 'prepared-v8/frwatc.for', build_dir / 'frwatc.for')
    shutil.copyfile(HERE / 'fh_state.inc', build_dir / 'fh_state.inc')
    shutil.copyfile(HERE / 'observer_control_driver.for', build_dir / 'driver.for')
    flags = ['-O0', '-fcheck=all', '-finit-real=snan', '-ffpe-trap=invalid,zero,overflow', '-ffixed-line-length-none']
    result = execute(['/usr/bin/gfortran', *flags, 'driver.for', 'frwatc.for', '-o', 'probe'], build_dir, 'build', 60)
    if result['returncode'] != 0:
        raise RuntimeError('Synthetic build failure')
    spec = importlib.util.spec_from_file_location('prior_frozen_reader', PREVIOUS / 'run_frozen_campaign.py')
    prior_reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior_reader)
    cases = json.loads((PREVIOUS / 'frozen-cases.json').read_text())
    if len(cases) != 29:
        raise ValueError('Control panel changed')
    results = []
    for case in cases:
        dest = target / case['id']
        dest.mkdir()
        for name in ['stdin.txt', 'case.json']:
            shutil.copyfile(base / case['id'] / name, dest / name)
        (dest / 'frwatc_history.on').touch()
        result = execute([build_dir / 'probe'], dest, 'execution', 60, dest / 'stdin.txt')
        result['ordinary_stdout_exact'] = sha(dest / 'execution.stdout') == sha(base / case['id'] / 'execution.stdout')
        try:
            if result['returncode'] != 0 or not result['ordinary_stdout_exact']:
                raise ValueError('Synthetic process/state parity failed')
            result['trace'] = read(dest / 'frwatc-history.txt', dest / 'transfers.jsonl', dest / 'ownership.jsonl')
            states = prior_reader.read_states((base / case['id'] / 'execution.stdout').read_text())
            transfers = [json.loads(line) for line in (dest / 'transfers.jsonl').read_text().splitlines()]
            if len(transfers) != len(case['modes']):
                raise ValueError('Synthetic map readback count mismatch')
            for index, transfer in enumerate(transfers):
                for side, stage in [('before', index + 1), ('after', index + 2)]:
                    expected_stocks = states[stage]['stocks']
                    for key in ['fine_liquid', 'fine_ice', 'fine_total', 'coarse_liquid', 'coarse_ice', 'coarse_total']:
                        actual = transfer[side][key]
                        expected = expected_stocks[key]
                        k = 16 * states[stage]['n'] + 64
                        gamma = k * 2**-53 / (1 - k * 2**-53)
                        bound = 2 * gamma * (abs(actual) + abs(expected))
                        if abs(actual - expected) > bound:
                            raise ValueError('Synthetic independent stock readback mismatch: ' + key)
            result['independent_stock_readback'] = True
            result['passed'] = True
        except (ValueError, OSError) as error:
            result.update(passed=False, error=str(error))
        result['case'] = case['id']
        save(dest / 'readback.json', result)
        results.append(result)
    by_id = {r['case']: r for r in results}
    required = {'F-low': 'F_positive_thin_support', 'G-low': 'G_update_support_skip',
                'H-low': 'H_frozen_liquid_clear', 'I-small': 'I_absolute_gate', 'I-middle': 'I_volumetric_gate'}
    recovered = {key: by_id[key].get('trace', {}).get('signature_counts', {}).get(tag, 0) > 0
                 for key, tag in required.items()}
    receipt = dict(cases=results, five_signatures=recovered,
                   passed=all(r['passed'] for r in results) and all(recovered.values()))
    save(target / 'receipt.json', receipt)
    if not receipt['passed']:
        raise RuntimeError('Positive controls failed; histories not invoked')
    print('29 synthetic controls passed; five signatures recovered', flush=True)


def output_check(root):
    import calendar
    import math
    outputs = root / 'output'
    required = {'H1.' + s + '.dat' for s in ['ebe', 'element', 'loss', 'pass', 'plot', 'soil', 'wat']}
    if {p.name for p in outputs.iterdir()} != required:
        raise ValueError('Output inventory mismatch')
    for path in outputs.iterdir():
        if not path.stat().st_size:
            raise ValueError('Empty output')
        for line in path.read_text().splitlines():
            tokens = line.split()
            stars = [t for t in tokens if set(t) == {'*'}]
            if stars:
                text = line.strip()
                decoration = text == '*** CAUTION ***' or (text.startswith(('** Soil Loss (', '** Maximum Soil Loss ', '** Soil Deposition (', '** Maximum Soil Deposition ')) and text.endswith(' **') and stars == ['**', '**'])
                if path.name != 'H1.loss.dat' or not decoration:
                    raise ValueError('Unknown star/overflow field')
            for token in tokens:
                try:
                    number = float(token.replace('D', 'E'))
                except ValueError:
                    continue
                if not math.isfinite(number):
                    raise ValueError('Nonfinite output')
    keys = set()
    for line in (outputs / 'H1.wat.dat').read_text().splitlines():
        c = line.split()
        if len(c) != 25 or not c[0].isdigit():
            continue
        key = tuple(map(int, c[:3]))
        if key in keys or float(c[21]) != 1800:
            raise ValueError('Duplicate clock or depth cap drift')
        keys.add(key)
    expected = {(ofe, day, year) for ofe in range(1, 4) for year in range(1, 17)
                for day in range(1, 367 if calendar.isleap(year) else 366)}
    if keys != expected:
        raise ValueError('Incomplete calendar')
    return dict(daily_keys=len(keys), output_hashes={p.name: sha(p) for p in outputs.iterdir()})


def histories(root, binary):
    previous = json.loads((OLD / 'sift-native-v1/receipt.json').read_text())
    accepted = {r['name']: r for r in json.loads((OLD / 'sift-readback-v2/receipt.json').read_text())['cases']}
    results = []
    for fixture in previous['cases']:
        name = fixture['fixture']['name']
        for flag in (0, 1):
            pair = root / (name + '-ks' + str(flag))
            pair.mkdir()
            members = []
            for kind, executable in [('baseline', PROBE / 'build/src/wepp'), ('observer', binary)]:
                dest = pair / kind
                runs = dest / 'runs'
                runs.mkdir(parents=True)
                (dest / 'output').mkdir()
                for filename, expected in fixture['input_hashes'].items():
                    source = OLD / 'sift-native-v1' / name / 'runs' / filename
                    if sha(source) != expected:
                        raise ValueError('History input drift')
                    shutil.copyfile(source, runs / filename)
                if flag:
                    soil = runs / 'p1.sol'
                    data = soil.read_bytes()
                    if data.count(b'\n3 0\n') != 1:
                        raise ValueError('Ambiguous soil header')
                    soil.write_bytes(data.replace(b'\n3 0\n', b'\n3 1\n'))
                (runs / 'frwatc_history.on').touch()
                inputs = {p.name: sha(p) for p in runs.iterdir()}
                save(dest / 'pre-execution.json', dict(binary_sha256=sha(executable), inputs=inputs,
                     freeze_sha256=sha(RAW / 'freeze.json'), scenario=name, header_ksflag=flag))
                result = execute([executable], runs, 'execution', 900, runs / 'p1.run')
                result.update(kind=kind, name=name, header_ksflag=flag, inputs=inputs,
                              binary_sha256=sha(executable))
                try:
                    if result['returncode'] != 0 or 'WEPP COMPLETED' not in (runs / 'execution.stdout').read_text():
                        raise ValueError('History process failed')
                    result.update(output_check(dest))
                    if any(sha(runs / filename) != digest for filename, digest in inputs.items()):
                        raise ValueError('Runtime input mutation')
                    if kind == 'baseline' and flag == 0 and result['output_hashes'] != accepted[name]['output_hashes']:
                        raise ValueError('Original baseline output drift')
                    if kind == 'observer':
                        result['trace'] = read(runs / 'frwatc-history.txt', dest / 'transfers.jsonl', dest / 'ownership.jsonl')
                        expected_days = {(o, d, y) for o in range(1, 4) for y in range(1, 17)
                                         for d in range(1, 367 if y % 4 == 0 else 366)}
                        observed = set(map(tuple, result['trace'].pop('daily_gate_keys')))
                        if observed != expected_days:
                            raise ValueError('Incomplete observer daily gate coverage')
                        result['trace']['complete_daily_gate_keys'] = len(observed)
                    result['passed'] = True
                except (ValueError, OSError) as error:
                    result.update(passed=False, error=str(error))
                save(dest / 'readback.json', result)
                members.append(result)
                print(name, flag, kind, 'passed', result['passed'], flush=True)
            parity = (all(r['passed'] for r in members)
                      and members[0]['inputs'] == members[1]['inputs']
                      and members[0]['output_hashes'] == members[1]['output_hashes'])
            result = dict(scenario=name + '-ks' + str(flag), accepted=parity, members=members)
            save(pair / 'receipt.json', result)
            results.append(result)
    receipt = dict(cases=results, passed=all(r['accepted'] for r in results))
    save(root / 'histories.json', receipt)
    return receipt['passed']


def run():
    frozen = json.loads((RAW / 'freeze.json').read_text())
    approval = json.loads((RAW / 'execution-approval.json').read_text())
    if approval['status'] != 'approved' or approval['freeze_sha256'] != sha(RAW / 'freeze.json'):
        raise ValueError('Missing exact execution review')
    for name, expected in approval['reviews'].items():
        if sha(HERE / name) != expected:
            raise ValueError('Execution review changed')
    verify(frozen)
    root = RAW / 'campaign-v1'
    root.mkdir()
    binary = build(root)
    controls(root)
    passed = histories(root, binary)
    verify(frozen)
    save(root / 'preservation.json', dict(all_frozen_dependencies_unchanged=True))
    if not passed:
        raise SystemExit('History campaign failed acceptance; all attempts retained')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['freeze', 'run'])
    args = parser.parse_args()
    freeze() if args.action == 'freeze' else run()
