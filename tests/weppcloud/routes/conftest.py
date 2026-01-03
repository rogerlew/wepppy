from types import SimpleNamespace

import pytest

from wepppy.weppcloud.utils import cap_guard

pytestmark = pytest.mark.skip("weppcloud route blueprints require optional runtime dependencies")


@pytest.fixture(autouse=True)
def _bypass_cap_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_user = SimpleNamespace(is_authenticated=True)
    monkeypatch.setattr(cap_guard, "current_user", stub_user, raising=False)
