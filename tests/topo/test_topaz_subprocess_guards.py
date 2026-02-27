import types

import pytest

from wepppy.topo.topaz import topaz as topaz_mod


pytestmark = pytest.mark.unit


class _DummyStdin:
    def __init__(self):
        self.writes = []
        self.closed = False

    def write(self, payload):
        self.writes.append(payload)

    def flush(self):
        return None

    def close(self):
        self.closed = True


class _DummyStdout:
    def __init__(self, lines):
        self._lines = [line.encode('utf-8') + b'\n' for line in lines]
        self._index = 0
        self.closed = False

    def readline(self):
        if self._index >= len(self._lines):
            return b''
        line = self._lines[self._index]
        self._index += 1
        return line

    def close(self):
        self.closed = True


class _DummyProc:
    def __init__(self, lines):
        self.stdin = _DummyStdin()
        self.stdout = _DummyStdout(lines)
        self._killed = False

    def poll(self):
        if self._killed:
            return -9
        if self.stdout._index < len(self.stdout._lines):
            return None
        return 0

    def kill(self):
        self._killed = True


class _EarlyExitDummyProc(_DummyProc):
    def __init__(self, lines, running_polls=1):
        super().__init__(lines)
        self._running_polls = running_polls

    def poll(self):
        if self._killed:
            return -9
        if self._running_polls > 0:
            self._running_polls -= 1
            return None
        return 0


def test_run_subprocess_nix_caps_output_lines(monkeypatch):
    proc = _DummyProc([f'line-{idx}' for idx in range(8)])
    runner = types.SimpleNamespace(topaz_wd='.')

    monkeypatch.setattr(topaz_mod, '_MAX_SUBPROCESS_OUTPUT_LINES', 3)
    monkeypatch.setattr(topaz_mod, 'Popen', lambda *_args, **_kwargs: proc)

    output = topaz_mod.TopazRunner._run_subprocess_nix(
        runner, cmd=['/fake/dednm'], stdin=None, verbose=False
    )

    assert output[0] == '[topaz output truncated: dropped 5 lines to cap memory]'
    assert output[1:] == ['line-5', 'line-6', 'line-7']


def test_run_subprocess_nix_aborts_prompt_loop(monkeypatch):
    prompt = 'ENTER 1 IF YOU WANT TO PROCEED WITH THESE VALUES'
    proc = _DummyProc([prompt, prompt, prompt, prompt])
    runner = types.SimpleNamespace(topaz_wd='.')

    monkeypatch.setattr(topaz_mod, '_MAX_SUBPROCESS_AUTO_RESPONSES', 2)
    monkeypatch.setattr(topaz_mod, 'Popen', lambda *_args, **_kwargs: proc)

    with pytest.raises(topaz_mod.TopazSubprocessGuardError):
        topaz_mod.TopazRunner._run_subprocess_nix(
            runner, cmd=['/fake/dednm'], stdin=None, verbose=False
        )

    assert proc._killed is True
    assert proc.stdin.writes == [b'1\n', b'1\n']


def test_run_subprocess_nix_drains_stdout_after_exit(monkeypatch):
    proc = _EarlyExitDummyProc(['first', 'second'], running_polls=1)
    runner = types.SimpleNamespace(topaz_wd='.')

    monkeypatch.setattr(topaz_mod, 'Popen', lambda *_args, **_kwargs: proc)

    output = topaz_mod.TopazRunner._run_subprocess_nix(
        runner, cmd=['/fake/dednm'], stdin=None, verbose=False
    )

    assert output == ['first', 'second']
