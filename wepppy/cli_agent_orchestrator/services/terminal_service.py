from __future__ import annotations


def send_input(terminal_id: str, payload: str) -> None:  # noqa: D401, ARG001
    """Send input to the target terminal; tests patch this function."""

    raise RuntimeError(f"terminal_service.send_input not stubbed for {terminal_id}")


__all__ = ["send_input"]
