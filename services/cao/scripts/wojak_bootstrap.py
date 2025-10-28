"""
Bridge Redis pub/sub with the Codex CLI for Wojak agent sessions.

This script is launched inside the CAO tmux session. It:
- Loads the session environment metadata (JWT token, run scope, Redis channels)
- Starts the Codex CLI as a subprocess
- Forwards Redis chat messages to Codex stdin
- Publishes Codex stdout/stderr lines back to Redis so status2 can stream them
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
from subprocess import Popen, PIPE
from typing import Optional

import redis

REDIS_DB = int(os.getenv("WOJAK_REDIS_DB", "2"))
REDIS_HOST = os.getenv("WOJAK_REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("WOJAK_REDIS_PORT", "6379"))
ENV_KEY_TEMPLATE = "agent:session:{session_id}:env"
DEFAULT_CODEX_COMMAND = os.getenv("WOJAK_CODEX_COMMAND", "codex --full-auto")

_stop_event = threading.Event()
_stdin_lock = threading.Lock()


def _load_env_from_redis(r: redis.Redis, session_id: str) -> dict[str, str]:
    env_key = os.getenv("AGENT_ENV_REDIS_KEY", ENV_KEY_TEMPLATE.format(session_id=session_id))
    payload = r.get(env_key)
    if not payload:
        return {}
    try:
        data = json.loads(payload)
        return {str(k): str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        return {}


def _ensure_required_env(r: redis.Redis) -> dict[str, str]:
    session_id = os.getenv("SESSION_ID")
    if not session_id:
        raise RuntimeError("SESSION_ID is required for Wojak bootstrap")

    preload = _load_env_from_redis(r, session_id)
    for key, value in preload.items():
        os.environ.setdefault(key, value)
    return preload


def _start_codex_process(env: dict[str, str]) -> Popen:
    command = env.get("WOJAK_CODEX_COMMAND", DEFAULT_CODEX_COMMAND)
    print(f"[WOJAK] launching command: {command}", file=sys.stderr)
    process = Popen(
        command,
        shell=True,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        bufsize=1,
        env=os.environ,
    )
    return process


def _publish_loop(stream, channel: str, r: redis.Redis, stream_type: str) -> None:
    while not _stop_event.is_set():
        line = stream.readline()
        if not line:
            break
        payload = {
            "type": "agent_output",
            "stream": stream_type,
            "content": line.rstrip("\n"),
            "timestamp": time.time(),
        }
        r.publish(channel, json.dumps(payload, separators=(",", ":")))


def _redis_listener(proc: Popen, r: redis.Redis, channel: str) -> None:
    pubsub = r.pubsub()
    pubsub.subscribe(channel)

    for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            payload = json.loads(message["data"])
        except json.JSONDecodeError:
            continue

        msg_type = payload.get("type")
        if msg_type == "user_message":
            content = payload.get("content")
            if not content:
                continue
            with _stdin_lock:
                if proc.stdin:
                    proc.stdin.write(content + "\n")
                    proc.stdin.flush()
        elif msg_type == "terminate":
            _stop_event.set()
            with _stdin_lock:
                if proc.stdin:
                    proc.stdin.write("exit\n")
                    proc.stdin.flush()
            break


def main() -> int:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    env_payload = _ensure_required_env(r)

    chat_channel = os.environ.get("REDIS_CHAT_CHANNEL")
    response_channel = os.environ.get("REDIS_RESPONSE_CHANNEL")

    if not chat_channel or not response_channel:
        raise RuntimeError("REDIS_CHAT_CHANNEL and REDIS_RESPONSE_CHANNEL must be set")

    process = _start_codex_process(env_payload)

    stdout_thread = threading.Thread(
        target=_publish_loop,
        args=(process.stdout, response_channel, r, "stdout"),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_publish_loop,
        args=(process.stderr, response_channel, r, "stderr"),
        daemon=True,
    )
    listener_thread = threading.Thread(
        target=_redis_listener,
        args=(process, r, chat_channel),
        daemon=True,
    )

    stdout_thread.start()
    stderr_thread.start()
    listener_thread.start()

    def _handle_signal(signum, frame):  # noqa: ANN001
        _stop_event.set()
        with _stdin_lock:
            if process.stdin:
                process.stdin.write("exit\n")
                process.stdin.flush()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    exit_code = process.wait()
    _stop_event.set()
    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)
    listener_thread.join(timeout=1)

    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Wojak bootstrap failed: {exc}", file=sys.stderr)
        sys.exit(1)
