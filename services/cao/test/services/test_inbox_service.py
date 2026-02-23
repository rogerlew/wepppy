import builtins
import logging
import base64
import os
import shlex
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

_TEST_HOME = Path("/tmp/wepppy-test-home")
_TEST_HOME.mkdir(parents=True, exist_ok=True)
os.environ["HOME"] = str(_TEST_HOME)

if "libtmux" not in sys.modules:
    libtmux_stub = types.ModuleType("libtmux")

    class _Server:  # pragma: no cover - ensured via provider imports
        def __init__(self, *args, **kwargs) -> None:  # noqa: D401, ANN001
            pass

    libtmux_stub.Server = _Server  # type: ignore[attr-defined]
    sys.modules["libtmux"] = libtmux_stub

if "frontmatter" not in sys.modules:
    frontmatter_stub = types.ModuleType("frontmatter")

    def _loads(text: str):
        return types.SimpleNamespace(metadata={}, content=text)

    frontmatter_stub.loads = _loads  # type: ignore[attr-defined]
    sys.modules["frontmatter"] = frontmatter_stub

if "watchdog.events" not in sys.modules:
    watchdog_stub = types.ModuleType("watchdog")
    watchdog_events_stub = types.ModuleType("watchdog.events")

    class _FileSystemEventHandler:  # pragma: no cover - used for import wiring
        pass

    class _FileModifiedEvent:
        def __init__(self, src_path: str = "") -> None:
            self.src_path = src_path

    watchdog_events_stub.FileSystemEventHandler = _FileSystemEventHandler  # type: ignore[attr-defined]
    watchdog_events_stub.FileModifiedEvent = _FileModifiedEvent  # type: ignore[attr-defined]
    watchdog_stub.events = watchdog_events_stub  # type: ignore[attr-defined]
    sys.modules["watchdog"] = watchdog_stub
    sys.modules["watchdog.events"] = watchdog_events_stub

import pytest
try:
    from cli_agent_orchestrator.models.inbox import InboxMessage, MessageStatus
    from cli_agent_orchestrator.services import inbox_service
    from cli_agent_orchestrator.providers import gemini as gemini_module
    GeminiProvider = gemini_module.GeminiProvider
except ModuleNotFoundError as exc:
    missing = getattr(exc, "name", "")
    if missing.startswith("cli_agent_orchestrator"):
        from wepppy.cli_agent_orchestrator.models.inbox import InboxMessage, MessageStatus
        from wepppy.cli_agent_orchestrator.services import inbox_service
        from wepppy.cli_agent_orchestrator.providers import gemini as gemini_module
        GeminiProvider = gemini_module.GeminiProvider
    else:
        raise


@pytest.mark.unit
def collection_error(monkeypatch, tmp_path):
    terminal_id = "abcd1234"
    message = InboxMessage(
        id=1,
        sender_id="sender",
        receiver_id=terminal_id,
        message="Please summarise the latest logs.",
        status=MessageStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )

    pending_calls = []

    def fake_get_pending_messages(tid, limit):
        pending_calls.append((tid, limit))
        return [message]

    updates = []

    def fake_update_message_status(message_id, status):
        updates.append((message_id, status))

    sent_inputs = []

    def fake_send_input(tid, payload):
        sent_inputs.append((tid, payload))

    monkeypatch.setattr(gemini_module, "AGENT_CONTEXT_DIR", tmp_path)

    provider = GeminiProvider(terminal_id, "sess", "win", agent_profile=None)
    provider._profile = SimpleNamespace(system_prompt="You are a terse summariser.")

    # Ensure we fail if gating tries to call get_status.
    def fail_get_status(*_args, **_kwargs):
        raise AssertionError("Gemini provider should skip status checks for headless delivery")

    provider.get_status = fail_get_status  # type: ignore[assignment]

    monkeypatch.setattr(inbox_service, "get_pending_messages", fake_get_pending_messages)
    monkeypatch.setattr(inbox_service, "update_message_status", fake_update_message_status)
    monkeypatch.setattr(inbox_service.terminal_service, "send_input", fake_send_input)
    monkeypatch.setattr(inbox_service.provider_manager, "get_provider", lambda _tid: provider)

    assert inbox_service.check_and_send_pending_messages(terminal_id) is True

    assert pending_calls == [(terminal_id, 1)]
    assert updates == [(message.id, MessageStatus.DELIVERED)]
    assert len(sent_inputs) == 1
    assert sent_inputs[0][0] == terminal_id

    expected_payload = "You are a terse summariser.\n\nPlease summarise the latest logs."
    encoded = base64.b64encode(expected_payload.encode("utf-8")).decode("ascii")
    flags = ["--approval-mode=yolo", "--output-format", "text"]
    flags_str = " ".join(shlex.quote(f) for f in flags)
    expected_command = (
        f"export CAO_MSG_B64='{encoded}'; "
        "tmp=$(mktemp -t cao_msg.XXXX); "
        "echo \"$CAO_MSG_B64\" | base64 -d > \"$tmp\"; "
        f"gemini -p \"$(cat \"$tmp\")\" {flags_str}; "
        "rm -f \"$tmp\""
    )
    assert sent_inputs[0][1] == expected_command


test_gemini_inbox_delivery_builds_non_interactive_command = collection_error


@pytest.mark.unit
def test_get_log_tail_expected_subprocess_exception_returns_empty_string(monkeypatch):
    import subprocess

    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="tail", timeout=1)

    monkeypatch.setattr(inbox_service.subprocess, "run", fake_run)
    assert inbox_service._get_log_tail("abcd1234", lines=5) == ""


@pytest.mark.unit
def test_get_log_tail_unexpected_runtime_error_propagates(monkeypatch):
    def fake_run(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(inbox_service.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="boom"):
        inbox_service._get_log_tail("abcd1234", lines=5)


@pytest.mark.unit
def test_has_idle_pattern_provider_lookup_failure_logs_and_returns_false(monkeypatch, caplog):
    terminal_id = "abcd1234"

    def raise_missing_terminal(*_args, **_kwargs):
        raise ValueError("missing terminal")

    monkeypatch.setattr(inbox_service, "_get_log_tail", lambda *_args, **_kwargs: "some output")
    monkeypatch.setattr(
        inbox_service.provider_manager,
        "get_provider",
        raise_missing_terminal,
    )

    caplog.set_level(logging.DEBUG, logger=inbox_service.logger.name)
    assert inbox_service._has_idle_pattern(terminal_id) is False
    assert "Unable to resolve provider/idle pattern" in caplog.text


@pytest.mark.unit
def test_has_idle_pattern_invalid_regex_logs_and_returns_false(monkeypatch, caplog):
    terminal_id = "abcd1234"

    class _Provider:
        def get_idle_pattern_for_log(self) -> str:
            return "("

    monkeypatch.setattr(inbox_service, "_get_log_tail", lambda *_args, **_kwargs: "some output")
    monkeypatch.setattr(inbox_service.provider_manager, "get_provider", lambda *_args, **_kwargs: _Provider())

    caplog.set_level(logging.ERROR, logger=inbox_service.logger.name)
    assert inbox_service._has_idle_pattern(terminal_id) is False
    assert "Invalid idle regex pattern" in caplog.text


@pytest.mark.unit
def test_has_idle_pattern_missing_idle_detector_logs_and_returns_false(monkeypatch, caplog):
    terminal_id = "abcd1234"

    class _Provider:
        pass

    monkeypatch.setattr(inbox_service, "_get_log_tail", lambda *_args, **_kwargs: "some output")
    monkeypatch.setattr(inbox_service.provider_manager, "get_provider", lambda *_args, **_kwargs: _Provider())

    caplog.set_level(logging.ERROR, logger=inbox_service.logger.name)
    assert inbox_service._has_idle_pattern(terminal_id) is False
    assert "does not support idle detection" in caplog.text


@pytest.mark.unit
def test_has_idle_pattern_none_idle_pattern_logs_and_returns_false(monkeypatch, caplog):
    terminal_id = "abcd1234"

    class _Provider:
        def get_idle_pattern_for_log(self):
            return None

    monkeypatch.setattr(inbox_service, "_get_log_tail", lambda *_args, **_kwargs: "some output")
    monkeypatch.setattr(inbox_service.provider_manager, "get_provider", lambda *_args, **_kwargs: _Provider())

    caplog.set_level(logging.ERROR, logger=inbox_service.logger.name)
    assert inbox_service._has_idle_pattern(terminal_id) is False
    assert "Invalid idle regex pattern" in caplog.text


@pytest.mark.unit
def test_check_and_send_pending_messages_import_error_falls_back_to_status_gating_and_delivers(monkeypatch):
    terminal_id = "abcd1234"
    message = InboxMessage(
        id=1,
        sender_id="sender",
        receiver_id=terminal_id,
        message="hello",
        status=MessageStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )

    def fake_get_pending_messages(tid, limit):
        assert tid == terminal_id
        assert limit == 1
        return [message]

    updates = []

    def fake_update_message_status(message_id, status):
        updates.append((message_id, status))

    sent_inputs = []

    def fake_send_input(tid, payload):
        sent_inputs.append((tid, payload))

    status_calls = []

    class _Provider:
        def get_status(self, tail_lines=None):
            status_calls.append(tail_lines)
            return inbox_service.TerminalStatus.IDLE

    provider = _Provider()

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name in {
            "cli_agent_orchestrator.providers.codex",
            "cli_agent_orchestrator.providers.gemini",
            "wepppy.cli_agent_orchestrator.providers.codex",
            "wepppy.cli_agent_orchestrator.providers.gemini",
        }:
            raise ModuleNotFoundError(name)
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(inbox_service, "get_pending_messages", fake_get_pending_messages)
    monkeypatch.setattr(inbox_service, "update_message_status", fake_update_message_status)
    monkeypatch.setattr(inbox_service.terminal_service, "send_input", fake_send_input)
    monkeypatch.setattr(inbox_service.provider_manager, "get_provider", lambda _tid: provider)

    assert inbox_service.check_and_send_pending_messages(terminal_id) is True
    assert status_calls == [inbox_service.INBOX_SERVICE_TAIL_LINES]
    assert sent_inputs == [(terminal_id, "hello")]
    assert updates == [(message.id, MessageStatus.DELIVERED)]


@pytest.mark.unit
def test_check_and_send_pending_messages_non_import_exception_during_provider_import_propagates(monkeypatch):
    terminal_id = "abcd1234"
    message = InboxMessage(
        id=1,
        sender_id="sender",
        receiver_id=terminal_id,
        message="hello",
        status=MessageStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )

    monkeypatch.setattr(inbox_service, "get_pending_messages", lambda *_args, **_kwargs: [message])

    updates = []

    def fake_update_message_status(message_id, status):
        updates.append((message_id, status))

    monkeypatch.setattr(inbox_service, "update_message_status", fake_update_message_status)
    monkeypatch.setattr(inbox_service.terminal_service, "send_input", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(inbox_service.provider_manager, "get_provider", lambda _tid: SimpleNamespace())

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name in {
            "cli_agent_orchestrator.providers.codex",
            "wepppy.cli_agent_orchestrator.providers.codex",
        }:
            raise RuntimeError("boom")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="boom"):
        inbox_service.check_and_send_pending_messages(terminal_id)

    assert updates == []
