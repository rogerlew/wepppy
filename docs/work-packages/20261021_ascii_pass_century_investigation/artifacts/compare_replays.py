"""Compare completed failed replays with the original failure artifacts."""
import hashlib
import json
from pathlib import Path
r = Path('/workdir/wepp-century-investigation-20261021')
a = Path(__file__).resolve().parent

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()

report = {'outputs':{}, 'hillslope_pass_unchanged':True}
for p in sorted((r/'original-output').iterdir()):
    paths=[p,r/'project-fork/wepp/output'/p.name,r/'probe/output'/p.name]
    hashes=[sha(f) for f in paths]
    report['outputs'][p.name]={'original_release_probe_sha256':hashes,'equal':len(set(hashes))==1, 'release_probe_equal':hashes[1]==hashes[2]}
original = json.loads((a/'date-audit.json').read_text())['files']
for name, info in original.items():
    if name.startswith('H'):
        assert sha(r/'project-fork/wepp/output'/name)==info['sha256'],name
        assert sha(r/'probe/output'/name)==info['sha256'],name
for lane in ['release','probe']:
    stdout=(r/f'{lane}-stdout.txt').read_text()
    stderr=(r/f'{lane}-stderr.txt').read_text()
    assert 'PASS components error: SOURCES3 date mismatch' in stdout
    assert 'STOP 1' in stderr
    report[lane]={'error':'SOURCES3 date mismatch','stderr':stderr,
                  'last_stdout_lines':stdout.splitlines()[-8:]}
report['all_outputs_equal']=all(x['equal'] for x in report['outputs'].values())
report['all_release_probe_outputs_equal']=all(x['release_probe_equal'] for x in report['outputs'].values())
print(json.dumps(report,indent=2))
