from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


def test_controllers_gl_template_sets_global_build_id() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "wepppy" / "weppcloud" / "controllers_js" / "templates" / "controllers.js.j2"
    contents = template.read_text(encoding="utf-8")

    assert "__weppControllersGlBuildId" in contents
    assert 'global.__weppControllersGlBuildId = "[[ build_date ]]"' in contents

