from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


def test_wepppy_modules_do_not_wildcard_import_nodb_core() -> None:
    root = Path(__file__).resolve().parents[1]
    offenders: list[str] = []

    for module_path in (root / "wepppy").rglob("*.py"):
        if "from wepppy.nodb.core import *" in module_path.read_text(encoding="utf-8"):
            offenders.append(str(module_path.relative_to(root)))

    assert offenders == []
