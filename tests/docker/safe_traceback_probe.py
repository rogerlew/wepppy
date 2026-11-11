"""Synthetic mounted-secret contract; run in the existing application image."""
from pathlib import Path
import json
import logging
import os
import stat
import sys
import time

from wepppy.observability import safe_traceback as safe, secret_profiles as profiles
from wepppy.observability.safe_logging import install

ROOT = Path('/run/secrets/weppcloud')
settings = {
    'SECRET_KEY_FILE': ROOT / 'secret_key',
    'SECURITY_PASSWORD_SALT_FILE': ROOT / 'salt',
    'WEPP_AUTH_JWT_SECRETS_FILE': ROOT / 'key_ring',
    'REDIS_PASSWORD_FILE': ROOT / 'redis_password',
    'WEPPCLOUDR_CONTROL_PLANE_TOKEN_FILE': Path('/run/secrets/weppcloudr/token'),
    'WEPPCLOUDR_TLS_KEY_FILE': Path('/run/secrets/weppcloudr/key'),
}
for name, path in settings.items():
    os.environ[name] = str(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o444
assert os.getuid() == 1000
install(profiles.WEB)
opened = []


def audit(event, args):
    if event == 'open' and isinstance(args[0], str) and '/run/secrets/' in args[0]:
        opened.append(args[0])


sys.addaudithook(audit)
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logging.info('ordinary successful progress')
assert opened == []
canary = settings['SECRET_KEY_FILE'].read_text().strip()
ring = settings['WEPP_AUTH_JWT_SECRETS_FILE'].read_text().strip().split(',')
os.environ['WEPPCLOUDR_K8S_IDENTITY_TOKEN_FILE'] = '/run/secrets/downstream-not-mounted'
try:
    raise RuntimeError('mounted-context ' + canary + ' ' + ' '.join(ring))
except RuntimeError as exc:
    logging.exception('web exception')
    text = safe.render_exception(exc, source_profile=profiles.WEB)
    assert 'RuntimeError' in text and 'mounted-context' in text
    assert canary not in text and all(key not in text for key in ring)
    print(text)
assert '/run/secrets/downstream-not-mounted' not in opened
os.environ['REDIS_PASSWORD_FILE'] = '/run/secrets/stale-not-mounted'
assert safe.render_exception(ValueError('shape-context'), source_profile=profiles.SHAPE).endswith('ValueError: shape-context\n')
assert '/run/secrets/stale-not-mounted' not in opened
os.environ['REDIS_PASSWORD_FILE'] = str(settings['REDIS_PASSWORD_FILE'])
control_values = [settings['WEPPCLOUDR_CONTROL_PLANE_TOKEN_FILE'].read_text().strip(),
                  settings['WEPPCLOUDR_TLS_KEY_FILE'].read_text().strip(),
                  Path('/var/run/secrets/kubernetes.io/serviceaccount/token').read_text().strip()]
text = safe.render_exception(ValueError('control-context ' + ' '.join(control_values)), source_profile=profiles.CONTROL_PLANE)
assert 'control-context' in text and all(value not in text for value in control_values)
print(text)
os.environ['SECRET_KEY_FILE'] = '/run/secrets/required-missing'
assert safe.render_exception(ValueError(canary), source_profile=profiles.WEB) == safe.UNAVAILABLE
os.environ['SECRET_KEY_FILE'] = str(settings['SECRET_KEY_FILE'])

# The host replaces this file while this same non-root process remains alive.
Path('/probe/ready').touch()
deadline = time.monotonic() + 20
while not Path('/probe/replaced').exists():
    if time.monotonic() > deadline:
        raise RuntimeError('host replacement did not arrive')
    time.sleep(0.02)
replacement = settings['SECRET_KEY_FILE'].read_text().strip()
assert replacement != canary
text = safe.render_exception(ValueError('replacement-context ' + replacement), source_profile=profiles.WEB)
assert replacement not in text and 'replacement-context' in text
print(text)
print(json.dumps({'uid': os.getuid(), 'gid': os.getgid(), 'mode': '0444',
                  'normal_source_reads': 0, 'replacement_observed': True,
                  'downstream_and_stale_paths_excluded': True, 'required_missing_fails_closed': True}))
