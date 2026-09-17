"""Run canonical CLI with private logs; redact its existing cookie diagnostic."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument('slug')
args=parser.parse_args()
if not args.slug.startswith('qa-freshness-'):
    raise ValueError('Disposable profile required')
auth=json.loads(Path('/tmp/wepppy-freshness-runtime-auth.json').read_text())
cookie='; '.join(key+'='+value for key,value in auth['cookies'].items())
cookie_file=Path('/tmp/wepppy-freshness-cookie.txt')
with os.fdopen(os.open(cookie_file,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600),'w') as stream:
    stream.write(cookie)
private_log=Path('/tmp/wepppy-freshness-profile-cli-private.log')
with os.fdopen(os.open(private_log,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600),'w') as stream:
    process=subprocess.run(['wctl','run-test-profile',args.slug,'--base-url',auth['host']+'/weppcloud',
                            '--cookie-file',str(cookie_file)],stdout=stream,stderr=subprocess.STDOUT)
text=private_log.read_text()
for secret in [cookie,auth['token'],*auth['cookies'].values()]:
    text=text.replace(secret,'[REDACTED]').replace(json.dumps(secret)[1:-1],'[REDACTED]')
text='\n'.join('[cookie payload diagnostic redacted]' if '"cookie"' in line else line for line in text.splitlines())+'\n'
Path(__file__).with_name('runtime_profile_canonical_cli.log').write_text(text)
Path(__file__).with_name('runtime_profile_canonical_cli_status.json').write_text(json.dumps({'exit_code':process.returncode,
    'acceptance':'Inspect per-request HTTP statuses; CLI exit alone is insufficient.'},indent=2)+'\n')
print('Canonical CLI exited',process.returncode,'; redacted evidence retained, verify per-request status.')
