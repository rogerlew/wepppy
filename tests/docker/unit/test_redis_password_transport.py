"""Execute the shell/password-file boundary, including Unicode framing parity."""
from pathlib import Path
import os
import subprocess

import pytest
from wepppy.config import redis_settings

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('data,accepted', [
    (b'normal\n', True), (b'normal\n\n', True), ('é 🔒:@ %\n'.encode(), True),
    ('inside\u00a0space\n'.encode(), True),
    (b'', False), (b'\n', False), (b'a\x00b', False), (b'\xff', False),
    (b'\xc0\x80', False), (b'\xed\xa0\x80', False), (b'\xf4\x90\x80\x80', False),
    (b'\xe2\x82', False), (b'a\rb', False), (b'a\nb', False),
] + [(f'{space}value\n'.encode(), False) for space in ['\x1c','\x1d','\x1e','\x1f','\u0085','\u00a0','\u1680','\u2003','\u2028','\u2029','\u202f','\u205f','\u3000']]
  + [(f'value{space}\n'.encode(), False) for space in [' ','\t','\r','\x1c','\u00a0','\u2003']])
def test_shell_and_native_file_framing_agree(tmp_path, monkeypatch, data, accepted):
    secret = tmp_path / 'password'
    secret.write_bytes(data)
    env = {**os.environ, 'REDIS_PASSWORD_FILE': str(secret)}
    result = subprocess.run(['sh', '-c', '. "$1"', 'probe', str(ROOT/'docker/redis-password.sh')],
                            env=env, capture_output=True)
    assert (result.returncode == 0) is accepted
    assert result.stdout == b''
    monkeypatch.setenv('REDIS_PASSWORD_FILE', str(secret))
    monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379/9')
    if accepted:
        assert redis_settings.redis_connection_kwargs(9)['password'].encode() == data.rstrip(b'\n')
    else:
        with pytest.raises(ValueError):
            redis_settings.redis_connection_kwargs(9)
