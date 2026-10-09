"""Optional Discord configuration must not prevent worker task imports."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.mark.parametrize("client_state", ["missing_token", "unreadable_token", "configured"])
def test_task_imports_with_optional_discord(tmp_path: Path, client_state: str) -> None:
    # A fresh interpreter exercises the entire project -> WEPP finalizer import
    # chain without leaking replacement modules into other tests. The missing
    # credential case performs a real open of a nonexistent file.
    package = tmp_path / "weppcloud2"
    client_dir = package / "discord_bot"
    client_dir.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (client_dir / "__init__.py").write_text("")
    if client_state == "unreadable_token":
        source = "raise PermissionError('Discord credential is unreadable')\n"
    else:
        source = textwrap.dedent("""\
            from pathlib import Path
            with (Path(__file__).parent / '.bot_token').open() as fp:
                token = fp.read()

            def send_discord_message(message):
                raise AssertionError('Imports must not send notifications')
        """)
    (client_dir / "discord_client.py").write_text(source)
    if client_state == "configured":
        (client_dir / ".bot_token").write_text("test-only-placeholder")

    script = textwrap.dedent("""\
        import importlib
        import sys
        from tests.conftest import _install_redis_stub

        # Reuse the suite's Redis isolation inside the fresh interpreter.
        redis_stub = _install_redis_stub.__wrapped__()
        next(redis_stub)
        importlib.import_module('wepppy.rq.project_rq')
        modules = [
            'wepppy.rq.wepp_rq_stage_finalize',
            'wepppy.rq.wepp_rq',
            'wepppy.rq.omni_rq',
            'wepppy.rq.batch_rq',
        ]
        for name in modules:
            module = importlib.import_module(name)
            if sys.argv[1] == 'configured':
                assert callable(module.send_discord_message), name
            else:
                assert module.send_discord_message is None, name
        next(redis_stub, None)
        print('TASK_IMPORTS_OK')
    """)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(tmp_path), str(Path(__file__).resolve().parents[2]), env.get("PYTHONPATH", "")]
    )
    result = subprocess.run(
        [sys.executable, "-c", script, client_state], env=env,
        capture_output=True, text=True, timeout=90, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "TASK_IMPORTS_OK" in result.stdout
    if client_state != "configured":
        assert "Discord notifications disabled" in result.stderr
