"""Run unchanged failed modules and unexecuted tails; retain every prior attempt."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path('/workdir/wepppy')
ART = Path(__file__).resolve().parent
OUT = ROOT / 'out/roads-parameterization-program-20261031/revision4-promotion'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ART / 'revision4-application-shards-declaration.json'
    declaration = json.loads(source.read_text())
    modules = {2: 'tests/microservices/test_rq_engine_upload_disturbed_routes.py',
               8: 'tests/wepp/interchange/test_roads_lifecycle.py'}
    planned = []
    for number, module in modules.items():
        spec = next(x for x in declaration['shards'] if x['shard'] == number)
        report = OUT / f'application-shard-{number}.jsonl'
        rows = [json.loads(x) for x in report.read_text().splitlines()]
        assert rows[-1]['$report_type'] == 'SessionFinish' and rows[-1]['exitstatus'] == 1
        failures = {x['nodeid'] for x in rows if x.get('outcome') == 'failed'}
        assert len(failures) == 1 and next(iter(failures)).split('::')[0] == module
        start = next(i for i, node in enumerate(spec['nodeids']) if node.split('::')[0] == module)
        selected = spec['nodeids'][start:]
        args = OUT / f'application-completion-shard{number}.args'
        assert not args.exists(), 'Never overwrite an attempted completion'
        args.write_text('\n'.join(selected) + '\n')
        command = ['wctl', 'run-pytest', '@' + str(args), '--maxfail=1',
                   f'--basetemp=/tmp/r4complete{number}',
                   '--report-log=' + str(OUT / f'application-completion-shard{number}.jsonl')]
        planned.append(dict(shard=number, original_report_sha256=sha(report),
                            failed_nodeids=sorted(failures), module=module,
                            nodeids=selected, args_sha256=sha(args), command=command))
    plan = dict(source_declaration_sha256=sha(source), script_sha256=sha(Path(__file__)),
                policy='Sequential fresh pytest processes, unchanged whole failed module and original complete tail. No source, test, assertion, timeout or credentials changed. Preserve original failures; deduplicate accepted node IDs.',
                planned=planned)
    (ART / 'revision4-application-completion-declaration.json').write_text(json.dumps(plan, indent=2) + '\n')
    results = []
    for spec in planned:
        log = OUT / f"application-completion-shard{spec['shard']}.log"
        with log.open('x') as stream:
            code = subprocess.run(spec['command'], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT).returncode
        results.append(dict(shard=spec['shard'], exit_code=code, log_sha256=sha(log)))
        print(json.dumps(results[-1]), flush=True)
    (ART / 'revision4-application-completion-exits.json').write_text(json.dumps(results, indent=2) + '\n')
    return 0 if all(x['exit_code'] == 0 for x in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
