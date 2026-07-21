from __future__ import annotations

import builtins

import pytest

from tools.wctl2 import __main__ as wctl_main


def test_missing_typer_prints_install_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    real_import = builtins.__import__

    def missing_typer(name: str, *args: object, **kwargs: object) -> object:
        if name == "typer":
            raise ModuleNotFoundError("No module named 'typer'", name="typer")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_typer)

    with pytest.raises(SystemExit) as exc_info:
        wctl_main._load_typer()

    assert exc_info.value.code == 1
    assert capsys.readouterr().err == (
        "wctl requires the 'typer' package for the current python3 interpreter.\n"
        "Install it with:\n"
        "  python3 -m pip install --user --break-system-packages typer\n"
    )
