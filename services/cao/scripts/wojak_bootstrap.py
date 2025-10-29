"""Headless bridge between Redis chat events and Codex non-interactive CLI."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

import redis

REDIS_DB = int(os.getenv("WOJAK_REDIS_DB", "2"))
REDIS_HOST = os.getenv("WOJAK_REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("WOJAK_REDIS_PORT", "6379"))
ENV_KEY_TEMPLATE = "agent:session:{session_id}:env"


def _load_env_from_redis(r: redis.Redis, session_id: str) -> dict[str, str]:
    env_key = os.getenv("AGENT_ENV_REDIS_KEY", ENV_KEY_TEMPLATE.format(session_id=session_id))
    payload = r.get(env_key)
    if not payload:
        return {}
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return {str(k): str(v) for k, v in data.items()}


def _ensure_required_env(r: redis.Redis) -> dict[str, str]:
    session_id = os.getenv("SESSION_ID")
    if not session_id:
        raise RuntimeError("SESSION_ID is required for Wojak bootstrap")

    preload = _load_env_from_redis(r, session_id)
    for key, value in preload.items():
        os.environ.setdefault(key, value)
    return preload


def _publish(r: redis.Redis, channel: str, message: Dict[str, Any]) -> None:
    message.setdefault("timestamp", time.time())
    r.publish(channel, json.dumps(message, separators=(",", ":")))


def _format_system(text: str) -> Dict[str, Any]:
    return {"type": "system", "content": text}


def _format_error(text: str) -> Dict[str, Any]:
    return {"type": "error", "content": text}


def _format_agent(text: str) -> Dict[str, Any]:
    return {"type": "agent_output", "content": text}


def _ensure_run_directory(path_str: str | None) -> Path | None:
    if not path_str:
        return None
    run_path = Path(path_str)
    if run_path.exists():
        return run_path
    return None


def _build_codex_command(run_dir: Path | None, thread_id: str | None, prompt: str) -> list[str]:
    base_cmd = [
        "codex",
        "exec",
        "--json",
        "--full-auto",
        "--skip-git-repo-check",
    ]
    if run_dir:
        base_cmd += ["--cd", str(run_dir)]

    if thread_id:
        return base_cmd + ["resume", thread_id, prompt]
    return base_cmd + [prompt]


def _handle_codex_event(
    event: Dict[str, Any],
    thread_state: Dict[str, str | None],
    publisher,
) -> None:
    event_type = event.get("type")

    if event_type == "thread.started":
        thread_id = event.get("thread_id")
        if thread_id:
            thread_state["id"] = thread_id
            publisher(_format_system(f"Codex session started (thread {thread_id})."))
        return

    if event_type == "item.started":
        item = event.get("item", {})
        if item.get("type") == "command_execution":
            command = item.get("command") or "command"
            publisher(_format_system(f"Running command: `{command}`"))
        return

    if event_type == "item.completed":
        item = event.get("item", {})
        item_type = item.get("type")

        if item_type == "agent_message":
            text = item.get("text", "").strip()
            if text:
                publisher(_format_agent(text))
        elif item_type == "reasoning":
            text = item.get("text", "").strip()
            if text:
                publisher(_format_system(text))
        elif item_type == "command_execution":
            command = item.get("command", "")
            output = item.get("aggregated_output", "").strip()
            status = item.get("status", "completed")
            parts = [f"Command `{command}` {status}."]
            if output:
                parts.append(output)
            publisher(_format_system("\n".join(parts)))
        elif item_type == "mcp_tool_call":
            tool = item.get("tool_name") or item.get("tool")
            args = item.get("arguments")
            publisher(_format_system(f"Tool call `{tool}` with arguments:\n{json.dumps(args, indent=2)}"))
        elif item_type == "file_change":
            publisher(_format_system("Agent applied a file change."))
        return

    if event_type == "turn.completed":
        usage = event.get("usage", {})
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        summary = "Turn completed."
        if input_tokens is not None or output_tokens is not None:
            summary += f" (input tokens: {input_tokens}, output tokens: {output_tokens})"
        publisher(_format_system(summary))
        return

    if event_type == "turn.failed":
        publisher(_format_error(json.dumps(event, indent=2)))
        return

    if event_type == "error":
        publisher(_format_error(event.get("error", "Codex reported an error.")))


def _decode_system_prompt(env: dict[str, Any]) -> str | None:
    encoded = env.get("WOJAK_SYSTEM_PROMPT_B64")
    if not encoded:
        return None
    try:
        return base64.b64decode(encoded).decode("utf-8")
    except Exception:
        return None


def main() -> int:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    env_payload = _ensure_required_env(redis_client)

    chat_channel = os.environ.get("REDIS_CHAT_CHANNEL")
    response_channel = os.environ.get("REDIS_RESPONSE_CHANNEL")
    run_id = os.environ.get("RUNID")
    run_dir = _ensure_run_directory(os.environ.get("RUN_DIR"))

    if not chat_channel or not response_channel or not run_id:
        raise RuntimeError("RUNID, REDIS_CHAT_CHANNEL, and REDIS_RESPONSE_CHANNEL must be set")

    if run_dir:
        os.chdir(run_dir)

    jwt_token = os.environ.get("AGENT_JWT_TOKEN")
    if jwt_token:
        os.environ.setdefault("JWT_TOKEN", jwt_token)

    system_prompt = _decode_system_prompt({**env_payload, **os.environ})

    full_response_channel = f"{run_id}:{response_channel}"
    publisher = lambda msg: _publish(redis_client, full_response_channel, msg)
    publisher(_format_system("Wojak headless Codex bridge ready."))

    thread_state: Dict[str, str | None] = {"id": None}

    def handle_user_message(content: str) -> None:
        prompt = content.strip()
        if not prompt:
            return

        thread_id = thread_state.get("id")

        effective_prompt = prompt
        if system_prompt and not thread_id:
            effective_prompt = f"{system_prompt.strip()}\n\nUser request:\n{prompt}"

        cmd = _build_codex_command(run_dir, thread_id, effective_prompt)
        publisher(_format_system(f"Invoking Codex: {' '.join(cmd)}"))

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=os.environ.copy(),
                cwd=run_dir,
            )
        except FileNotFoundError:
            publisher(_format_error("Codex CLI not found on PATH."))
            return

        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                publisher(_format_system(line))
                continue
            _handle_codex_event(event, thread_state, publisher)

        if process.stderr is not None:
            stderr_output = process.stderr.read().strip()
            if stderr_output:
                publisher(_format_system(stderr_output))

        exit_code = process.wait()
        if exit_code != 0:
            publisher(_format_error(f"Codex exited with status {exit_code}"))

    full_chat_channel = f"{run_id}:{chat_channel}"
    pubsub = redis_client.pubsub()
    pubsub.subscribe(full_chat_channel)

    stop_requested = False

    try:
        for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                payload = json.loads(message["data"])
            except json.JSONDecodeError:
                continue

            msg_type = payload.get("type")
            if msg_type == "user_message":
                handle_user_message(payload.get("content", ""))
            elif msg_type == "terminate":
                publisher(_format_system("Termination requested; shutting down."))
                stop_requested = True
                break

    finally:
        pubsub.close()

    return 0 if not stop_requested else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Wojak bootstrap failed: {exc}", file=sys.stderr)
        sys.exit(1)
