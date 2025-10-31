from __future__ import annotations


class _ProviderManager:
    """Simple placeholder so tests can monkeypatch `get_provider`."""

    def get_provider(self, terminal_id: str):  # noqa: ANN001 - tests patch this
        raise LookupError(f"No provider registered for {terminal_id}")


provider_manager = _ProviderManager()

__all__ = ["provider_manager"]
