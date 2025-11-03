import os
import shlex
import sys
import types
from pathlib import Path

import pytest

_TEST_HOME = Path("/tmp/wepppy-test-home")
_TEST_HOME.mkdir(parents=True, exist_ok=True)
os.environ["HOME"] = str(_TEST_HOME)

if "frontmatter" not in sys.modules:
    frontmatter_stub = types.ModuleType("frontmatter")

    def _loads(text: str):
        return types.SimpleNamespace(metadata={}, content=text)

    frontmatter_stub.loads = _loads  # type: ignore[attr-defined]
    sys.modules["frontmatter"] = frontmatter_stub

try:
    from cli_agent_orchestrator.models.agent_profile import AgentProfile
    from cli_agent_orchestrator.models.terminal import TerminalStatus
    from cli_agent_orchestrator.providers import gemini as gemini_module
except ModuleNotFoundError as exc:  # pragma: no cover - fallback for bundled installs
    missing = getattr(exc, "name", "")
    if missing.startswith("cli_agent_orchestrator"):
        from wepppy.cli_agent_orchestrator.models.agent_profile import AgentProfile
        from wepppy.cli_agent_orchestrator.models.terminal import TerminalStatus
        from wepppy.cli_agent_orchestrator.providers import gemini as gemini_module
    else:
        raise


class _DummyTmux:
    """Minimal tmux client stub for provider tests."""

    def __init__(self) -> None:
        self.sent_commands: list[str] = []
        self.history: str = ""

    def send_keys(self, session_name: str, window_name: str, keys: str) -> None:
        self.sent_commands.append(keys)

    def get_history(self, session_name: str, window_name: str, tail_lines=None) -> str:
        return self.history


@pytest.fixture
def tmux_stub(monkeypatch, tmp_path):
    """Provide isolated tmux stub and patched module constants."""
    stub = _DummyTmux()
    monkeypatch.setattr(gemini_module, "tmux_client", stub)
    monkeypatch.setattr(gemini_module, "wait_for_shell", lambda *args, **kwargs: True)
    monkeypatch.setattr(gemini_module, "AGENT_CONTEXT_DIR", tmp_path)
    return stub


@pytest.mark.unit
def test_initialize_writes_system_prompt(tmp_path, tmux_stub, monkeypatch):
    profile = AgentProfile(name="dev", description="Developer", system_prompt="Keep output concise.")
    monkeypatch.setattr(gemini_module, "load_agent_profile", lambda *_: profile)

    provider = gemini_module.GeminiProvider("abcd1234", "sess", "win", "dev")

    assert provider.initialize() is True
    context_dir = Path(tmp_path, "abcd1234")
    system_md = context_dir / "system.md"
    assert system_md.exists()
    assert "Keep output concise." in system_md.read_text()

    expected_export = f"export GEMINI_SYSTEM_MD={shlex.quote(str(system_md))}"
    assert expected_export in tmux_stub.sent_commands
    assert tmux_stub.sent_commands[-1] == "gemini"
    assert provider.status == TerminalStatus.IDLE


@pytest.mark.unit
@pytest.mark.parametrize(
    ("history", "expected"),
    [
        ("Type your message or @path/to/file", TerminalStatus.IDLE),
        ("Confirm deployment? (y/n)", TerminalStatus.WAITING_USER_ANSWER),
        ("Error: quota exceeded", TerminalStatus.ERROR),
        ("Streaming response chunk...", TerminalStatus.PROCESSING),
    ],
)
def test_status_detection(tmp_path, tmux_stub, history, expected):
    tmux_stub.history = history
    provider = gemini_module.GeminiProvider("ffffeeee", "sess", "win", None)

    status = provider.get_status()
    assert status == expected
    assert provider.status == expected


@pytest.mark.unit
def test_extract_last_message_strips_ansi(tmux_stub):
    provider = gemini_module.GeminiProvider("1234abcd", "sess", "win", None)
    ansi_output = "\x1b[32mAll good\x1b[0m\n\n\x1b[31mStill processing\x1b[0m"

    result = provider.extract_last_message_from_script(ansi_output)
    assert result == "All good\nStill processing"


@pytest.mark.unit
def test_cleanup_removes_context(tmp_path, tmux_stub, monkeypatch):
    profile = AgentProfile(name="dev", description="Developer", system_prompt="Persist this.")
    monkeypatch.setattr(gemini_module, "load_agent_profile", lambda *_: profile)

    provider = gemini_module.GeminiProvider("beadfeed", "sess", "win", "dev")
    provider.initialize()
    context_dir = Path(tmp_path, "beadfeed")
    assert context_dir.exists()

    provider.cleanup()
    assert not context_dir.exists()


collection_error = test_initialize_writes_system_prompt
