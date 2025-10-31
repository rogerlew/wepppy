from datetime import datetime, timezone
from types import SimpleNamespace
import base64
import shlex

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
def test_gemini_inbox_delivery_builds_non_interactive_command(monkeypatch, tmp_path):
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
