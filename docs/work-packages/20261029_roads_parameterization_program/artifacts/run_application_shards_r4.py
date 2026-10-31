"""Complete the unchanged application test inventory in isolated pytest processes."""
from pathlib import Path
import collections
import concurrent.futures
import hashlib
import json
import subprocess

ROOT = Path('/workdir/wepppy')
OUT = ROOT / 'out/roads-parameterization-program-20261031/revision4-promotion'
ART = ROOT / 'docs/work-packages/20261029_roads_parameterization_program/artifacts'
WORKERS = 8
SLOW = 'tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    collection = OUT / 'application-collection.log'
    nodes = [line.strip() for line in collection.read_text().splitlines()
             if line.startswith('tests/') and '::' in line]
    assert len(nodes) == len(set(nodes)) == 12955
    modules = collections.defaultdict(list)
    for node in nodes:
        modules[node.split('::')[0]].append(node)
    shards = [[] for _ in range(WORKERS)]
    for i, node in enumerate(modules.pop(SLOW)):
        shards[i % WORKERS].append(node)
    for name, items in sorted(modules.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        target = min(range(WORKERS), key=lambda i: len(shards[i]))
        shards[target].extend(items)
    assert sorted(n for shard in shards for n in shard) == sorted(nodes)
    specs = []
    for i, selected in enumerate(shards, 1):
        args = OUT / f'application-shard-{i}.args'
        assert not args.exists(), 'Retain each declared attempt; never silently overwrite a shard'
        args.write_text('\n'.join(selected) + '\n')
        command = ['wctl', 'run-pytest', '@' + str(args), '--maxfail=1',
                   '--basetemp=/tmp/r4s' + str(i),
                   '--report-log=' + str(OUT / f'application-shard-{i}.jsonl')]
        specs.append(dict(shard=i, cases=len(selected), nodeids=selected,
                          args_sha256=sha(args), command=command))
    declaration = dict(collected=len(nodes), collection_sha256=sha(collection),
        script_sha256=sha(__file__), workers=WORKERS, shards=specs,
        inventory_exactly_once=True, source_commit=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        policy='All collected node IDs exactly once. Preserve ordinary module grouping except the large soil-writer module, whose independent parameterized cases are distributed. No tests/assertions changed. Prior interrupted serial run excluded from accepted counts.',
        binaries={n: sha(ROOT / 'wepp_runner/bin' / n) for n in ('wepp_261029', 'wepp_261029_hill')})
    (ART / 'revision4-application-shards-declaration.json').write_text(json.dumps(declaration, indent=2) + '\n')
    def execute(spec):
        log = OUT / f"application-shard-{spec['shard']}.log"
        with log.open('w') as output:
            code = subprocess.run(spec['command'], cwd=ROOT, stdout=output, stderr=subprocess.STDOUT).returncode
        print('Shard', spec['shard'], 'exit', code, flush=True)
        return dict(shard=spec['shard'], exit_code=code, log=str(log), log_sha256=sha(log))
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        receipts = list(pool.map(execute, specs))
    (OUT / 'application-shards-exits.json').write_text(json.dumps(receipts, indent=2) + '\n')
    raise SystemExit(0 if all(r['exit_code'] == 0 for r in receipts) else 1)


if __name__ == '__main__':
    main()
