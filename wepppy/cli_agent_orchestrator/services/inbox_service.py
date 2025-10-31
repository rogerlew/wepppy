from __future__ import annotations

import base64
import shlex
from typing import Sequence

from wepppy.cli_agent_orchestrator.models.inbox import InboxMessage, MessageStatus
from wepppy.cli_agent_orchestrator.providers.gemini import GeminiProvider
from wepppy.cli_agent_orchestrator.providers.manager import provider_manager
from wepppy.cli_agent_orchestrator.services import terminal_service

__all__ = [
    "check_and_send_pending_messages",
    "get_pending_messages",
    "update_message_status",
]


def get_pending_messages(terminal_id: str, limit: int = 1) -> Sequence[InboxMessage]:  # noqa: D401
    """Return pending messages; overridden by tests."""

    return []


def update_message_status(message_id: int, status: MessageStatus) -> None:  # noqa: D401, ARG001
    """Update message status; overridden by tests."""

    return None


def _apply_system_prompt(provider: GeminiProvider, payload: str) -> str:
    profile = getattr(provider, "_profile", None)
    system_prompt = getattr(profile, "system_prompt", None)
    if system_prompt:
        return f"{system_prompt.strip()}\n\n{payload.lstrip()}"
    return payload


def _build_gemini_command(payload: str) -> str:
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    flags = ["--approval-mode=yolo", "--output-format", "text"]
    flags_str = " ".join(shlex.quote(flag) for flag in flags)
    return (
        f"export CAO_MSG_B64='{encoded}'; "
        "tmp=$(mktemp -t cao_msg.XXXX); "
        "echo \"$CAO_MSG_B64\" | base64 -d > \"$tmp\"; "
        f"gemini -p \"$(cat \"$tmp\")\" {flags_str}; "
        "rm -f \"$tmp\""
    )


def _deliver_with_gemini(terminal_id: str, message: InboxMessage, provider: GeminiProvider) -> None:
    payload = _apply_system_prompt(provider, message.message)
    command = _build_gemini_command(payload)
    terminal_service.send_input(terminal_id, command)


def _deliver_plain(terminal_id: str, message: InboxMessage) -> None:
    terminal_service.send_input(terminal_id, message.message)


def check_and_send_pending_messages(terminal_id: str) -> bool:
    """Deliver the next pending message for `terminal_id`.

    Tests patch all side-effecting collaborators (database access, providers,
    terminal I/O) so this function only needs to orchestrate control flow.
    """

    messages = get_pending_messages(terminal_id, limit=1)
    if not messages:
        return False

    message = messages[0]

    try:
        provider = provider_manager.get_provider(terminal_id)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Provider not available for terminal {terminal_id}") from exc

    try:
        if isinstance(provider, GeminiProvider):
            _deliver_with_gemini(terminal_id, message, provider)
        else:
            _deliver_plain(terminal_id, message)
        update_message_status(message.id, MessageStatus.DELIVERED)
        return True
    except Exception as exc:  # noqa: BLE001
        update_message_status(message.id, MessageStatus.FAILED)
        raise exc
