#!/usr/bin/env python3
"""Fixed-principal Culvert renewal operator and restricted SSH receiver.

Only Python's standard library is required. Never print token-bearing exceptions.
See docs/culvert-at-risk-integration/jwt-renewal.md for installation and recovery.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

TTL = 90 * 86400
RENEW_BEFORE = 30 * 86400
MAX_TOKEN = 16384
ENDPOINT = "https://wepp.cloud/rq-engine/api/culverts-wepp-batch/"
TOKEN_PATH = Path("/workdir/culvert_app_instance_dir/.weppcloud-auth/token")
CONFIG_DIR = Path.home() / ".config/weppcloud-culvert-renewal"
STATE_DIR = Path.home() / ".local/state/weppcloud-culvert-renewal"
IDENTITY = {
    "sub": "culvert-batch-submit-90d",
    "aud": "rq-engine",
    "token_class": "service",
    "service_groups": "culverts",
    "scope": "culvert:batch:submit",
}


class RotationError(RuntimeError):
    """Sanitized operational failure safe for the journal."""


def metadata(token: str) -> dict:
    """Inspect untrusted claims for scheduling; HTTPS separately verifies trust."""
    try:
        if not 1 <= len(token) <= MAX_TOKEN or any(c.isspace() for c in token):
            raise ValueError
        parts = token.split(".")
        if len(parts) != 3 or not all(parts):
            raise ValueError
        claims = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
        if not isinstance(claims, dict):
            raise ValueError
        if any(claims.get(k) != v for k, v in IDENTITY.items()):
            raise ValueError
        if set(claims) - (set(IDENTITY) | {"iat", "exp", "jti", "iss"}):
            raise ValueError
        if any(type(claims.get(k)) is not int for k in ("iat", "exp")):
            raise ValueError
        if not 0 < claims["exp"] - claims["iat"] <= TTL:
            raise ValueError
        if not isinstance(claims.get("jti"), str) or not claims["jti"]:
            raise ValueError
    except (ValueError, TypeError, UnicodeError) as exc:
        raise RotationError("invalid token structure or registered identity") from None
    return {**IDENTITY, "iat": claims["iat"], "exp": claims["exp"],
            "jti": claims["jti"], "sha256": hashlib.sha256(token.encode()).hexdigest()}


def private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise RotationError("credential/state directory must be owned by operator and mode 0700")


def read_private(path: Path) -> str | None:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "r") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise RotationError("credential file must be regular, operator-owned and mode 0600")
        text = stream.read(MAX_TOKEN + 1)
    if len(text) > MAX_TOKEN:
        raise RotationError("credential file too large")
    return text.strip()


def atomic_write(path: Path, text: str) -> None:
    # Check existing target without following symlinks, even though replace is atomic.
    if path.exists() or path.is_symlink():
        read_private(path)
    fd, name = tempfile.mkstemp(prefix=".renew-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextlib.contextmanager
def locked(directory: Path):
    private_directory(directory)
    fd = os.open(directory / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def verify(token: str) -> None:
    """Authentication must reach missing-file validation; never submit model work."""
    claims = metadata(token)
    now = int(time.time())
    if claims["iat"] > now + 60 or claims["exp"] <= now:
        raise RotationError("candidate token is not currently valid")
    request = urllib.request.Request(ENDPOINT, data=b"", method="POST",
                                     headers={"Authorization": "Bearer " + token})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            code, body = response.status, response.read(65536)
    except urllib.error.HTTPError as exc:
        code, body = exc.code, exc.read(65536)
        exc.close()
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RotationError("API verification transport failure") from None
    try:
        payload = json.loads(body)
        accepted = (code == 400 and payload.get("error", {}).get("code") == "validation_error"
                    and any(e.get("code") == "missing_file" and e.get("path") == "payload.zip"
                            for e in payload.get("errors", [])))
    except (ValueError, AttributeError, TypeError):
        accepted = False
    if not accepted:
        raise RotationError(f"API rejected verification (HTTP {code})")


def receiver(action: str, token_path: Path = TOKEN_PATH, candidate: str | None = None) -> dict:
    if action not in {"status", "install"}:
        raise RotationError("receiver command denied")
    with locked(token_path.parent):
        current = read_private(token_path)
        old = metadata(current) if current is not None else None
        if action == "status":
            return {"installed": old}
        if candidate is None:
            raw = sys.stdin.read(MAX_TOKEN + 1)
            if len(raw) > MAX_TOKEN:
                raise RotationError("candidate input too large")
            candidate = raw.strip()
        new = metadata(candidate)
        verify(candidate)
        if current is not None:
            atomic_write(token_path.with_name("previous"), current + "\n")
        atomic_write(token_path, candidate + "\n")
        installed = metadata(read_private(token_path))
        if installed != new:
            raise RotationError("installed token readback mismatch")
        return {"installed": installed}


def run_private(command: list[str], *, input_text: str | None = None, timeout: int = 120) -> str:
    try:
        result = subprocess.run(command, input=input_text, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        raise RotationError("operator subprocess unavailable or timed out") from None
    if result.returncode:
        # Child output may contain credentials; do not forward it to systemd logs.
        raise RotationError(f"operator subprocess failed (exit {result.returncode}); inspect service/receiver health")
    return result.stdout


def remote(action: str, candidate: str | None = None) -> dict:
    command = ["/usr/bin/ssh", "-F", "/dev/null", "-i", str(CONFIG_DIR / "id_ed25519"),
               "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "UserKnownHostsFile=" + str(CONFIG_DIR / "known_hosts"),
               "-o", "ConnectTimeout=15", "-o", "HostName=wepp2.tail305ec9.ts.net",
               "-o", "HostKeyAlias=wepp2", "roger@wepp2", action]
    try:
        result = json.loads(run_private(command, input_text=candidate))
        if not isinstance(result, dict) or set(result) != {"installed"}:
            raise ValueError
        return result
    except ValueError:
        raise RotationError("invalid receiver receipt") from None


def renew(force: bool = False) -> dict:
    current = remote("status")["installed"]
    if current and not force and current["exp"] - int(time.time()) > RENEW_BEFORE:
        return {"status": "not_due", "installed": current}
    command = ["/usr/local/bin/wctl", "issue-auth-token", IDENTITY["sub"],
               "--audience", IDENTITY["aud"], "--scope", IDENTITY["scope"],
               "--claim", "token_class=service", "--claim", "service_groups=culverts",
               "--expires-in", str(TTL), "--json"]
    try:
        token = json.loads(run_private(command))["token"]
    except (ValueError, KeyError, TypeError):
        raise RotationError("invalid issuer response") from None
    expected = metadata(token)
    verify(token)
    if current and expected["jti"] == current["jti"]:
        raise RotationError("issuer reused credential identifier")
    installed = remote("install", token)["installed"]
    readback = remote("status")["installed"]
    if installed != expected or readback != expected:
        raise RotationError("remote installed token readback mismatch")
    return {"status": "renewed", "installed": readback}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("renew", "receive"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        if args.mode == "receive":
            receipt = receiver(os.environ.get("SSH_ORIGINAL_COMMAND", ""))
        else:
            with locked(STATE_DIR):
                try:
                    receipt = renew(args.force)
                except (RotationError, OSError, ValueError, TypeError, KeyError):
                    atomic_write(STATE_DIR / "last-attempt.json", json.dumps(
                        {"status": "failed", "checked_at": int(time.time())}) + "\n")
                    raise
                receipt["checked_at"] = int(time.time())
                atomic_write(STATE_DIR / "last-attempt.json", json.dumps(receipt) + "\n")
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (RotationError, OSError, ValueError, TypeError, KeyError) as exc:
        # Deliberate CLI boundary: only RotationError has vetted nonsecret messages.
        detail = str(exc) if isinstance(exc, RotationError) else type(exc).__name__
        print("Culvert token renewal failed: " + detail, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
