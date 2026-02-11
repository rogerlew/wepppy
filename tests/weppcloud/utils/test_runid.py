from __future__ import annotations

import pytest

from wepppy.weppcloud.utils import runid as runid_utils


pytestmark = pytest.mark.unit


def test_generate_runid_prefixes_mdobre(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runid_utils.awesome_codename, "generate_codename", lambda: "silent river")

    generated = runid_utils.generate_runid("mdobre@example.com")

    assert generated == "mdobre-silent-river"


def test_generate_runid_prefixes_srivas42(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runid_utils.awesome_codename, "generate_codename", lambda: "hidden ridge")

    generated = runid_utils.generate_runid("srivas42@example.com")

    assert generated == "srivas42-hidden-ridge"


def test_generate_runid_does_not_prefix_other_users(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runid_utils.awesome_codename, "generate_codename", lambda: "amber plains")

    generated = runid_utils.generate_runid("someone@example.com")

    assert generated == "amber-plains"
