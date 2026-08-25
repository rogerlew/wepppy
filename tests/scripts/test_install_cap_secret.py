from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_INSTALLER = _REPO_ROOT / "docker" / "install-cap-secret.sh"


def test_installer_captures_secret_before_compose_uid_probe_consumes_stdin(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    docker_dir = project / "docker"
    secret_dir = docker_dir / "secrets"
    bin_dir = tmp_path / "bin"
    secret_dir.mkdir(parents=True)
    bin_dir.mkdir()
    installer = docker_dir / "install-cap-secret.sh"
    installer.write_bytes(_INSTALLER.read_bytes())
    installer.chmod(0o755)

    preparer = docker_dir / "prepare-cap-runtime.sh"
    preparer.write_text("#!/bin/bash\nset -euo pipefail\n", encoding="utf-8")
    preparer.chmod(0o755)

    wctl = bin_dir / "wctl"
    wctl.write_text(
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        "if [[ \"$*\" == *\"config --format json\"* ]]; then\n"
        "  printf '%s\\n' '{\"services\":{\"cap\":{\"secrets\":[{\"source\":\"cap_secret\"}]}}}'\n"
        "elif [[ \"$*\" == *\"docker compose run\"* ]]; then\n"
        "  cat >/dev/null\n"
        "  printf '10001\\n'\n"
        "else\n"
        "  exit 90\n"
        "fi\n",
        encoding="utf-8",
    )
    wctl.chmod(0o755)
    setfacl = bin_dir / "setfacl"
    setfacl.write_text("#!/bin/bash\nset -euo pipefail\n", encoding="utf-8")
    setfacl.chmod(0o755)
    getfacl = bin_dir / "getfacl"
    getfacl.write_text(
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        "printf '%s\\n' 'user::rw-' 'user:10001:r--' 'group::---' 'mask::r--' 'other::---'\n",
        encoding="utf-8",
    )
    getfacl.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    result = subprocess.run(
        [str(installer)],
        input="forest-cap-secret\n",
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    secret = secret_dir / "cap_secret"
    assert secret.read_text(encoding="utf-8") == "forest-cap-secret\n"
