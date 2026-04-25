from __future__ import annotations

from types import SimpleNamespace

import pytest

from wepppy.nodb.base import TriggerEvents
from wepppy.nodb.mods.disturbed.disturbed import Disturbed

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


class _NoopLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return


def _controller_stubs(*, defer_rebuild: bool = False):
    return (
        SimpleNamespace(
            logger=_NoopLogger(),
            _defer_disturbed_management_rebuild=defer_rebuild,
        ),
        SimpleNamespace(logger=_NoopLogger()),
    )


def test_on_routes_landuse_event_with_multi_ofe(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("on-landuse-mofe")
    landuse, soils = _controller_stubs(defer_rebuild=True)
    calls: list[str] = []

    monkeypatch.setattr(Disturbed, "wepp_instance", property(lambda self: SimpleNamespace(_multi_ofe=True)))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(
        Disturbed,
        "remap_landuse",
        lambda self, *, rebuild_managements=True: calls.append(
            f"remap_landuse:{rebuild_managements}"
        ),
    )
    monkeypatch.setattr(Disturbed, "spatialize_treecanopy", lambda self: calls.append("spatialize_treecanopy") or 1)
    monkeypatch.setattr(
        Disturbed,
        "remap_mofe_landuse",
        lambda self, *, rebuild_managements=True: calls.append(
            f"remap_mofe_landuse:{rebuild_managements}"
        ),
    )

    disturbed.on(TriggerEvents.LANDUSE_DOMLC_COMPLETE)

    assert calls == [
        "remap_landuse:False",
        "spatialize_treecanopy",
        "remap_mofe_landuse:False",
    ]


def test_on_routes_landuse_event_without_defer_flag_keeps_immediate_rebuilds(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("on-landuse-mofe-no-defer")
    landuse, soils = _controller_stubs(defer_rebuild=False)
    calls: list[str] = []

    monkeypatch.setattr(Disturbed, "wepp_instance", property(lambda self: SimpleNamespace(_multi_ofe=True)))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(
        Disturbed,
        "remap_landuse",
        lambda self, *, rebuild_managements=True: calls.append(
            f"remap_landuse:{rebuild_managements}"
        ),
    )
    monkeypatch.setattr(Disturbed, "spatialize_treecanopy", lambda self: calls.append("spatialize_treecanopy") or 1)
    monkeypatch.setattr(
        Disturbed,
        "remap_mofe_landuse",
        lambda self, *, rebuild_managements=True: calls.append(
            f"remap_mofe_landuse:{rebuild_managements}"
        ),
    )

    disturbed.on(TriggerEvents.LANDUSE_DOMLC_COMPLETE)

    assert calls == [
        "remap_landuse:True",
        "spatialize_treecanopy",
        "remap_mofe_landuse:True",
    ]


def test_on_routes_landuse_event_without_multi_ofe(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("on-landuse-single")
    landuse, soils = _controller_stubs()
    calls: list[str] = []

    monkeypatch.setattr(Disturbed, "wepp_instance", property(lambda self: SimpleNamespace(_multi_ofe=False)))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(
        Disturbed,
        "remap_landuse",
        lambda self, *, rebuild_managements=True: calls.append(
            f"remap_landuse:{rebuild_managements}"
        ),
    )
    monkeypatch.setattr(Disturbed, "spatialize_treecanopy", lambda self: calls.append("spatialize_treecanopy") or 0)
    monkeypatch.setattr(
        Disturbed,
        "remap_mofe_landuse",
        lambda self, *, rebuild_managements=True: calls.append(
            f"remap_mofe_landuse:{rebuild_managements}"
        ),
    )

    disturbed.on(TriggerEvents.LANDUSE_DOMLC_COMPLETE)

    assert calls == ["remap_landuse:True", "spatialize_treecanopy"]


def test_on_routes_soils_event_to_mofe_when_enabled(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("on-soils-mofe")
    landuse, soils = _controller_stubs()
    calls: list[str] = []

    monkeypatch.setattr(Disturbed, "wepp_instance", property(lambda self: SimpleNamespace(_multi_ofe=True)))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "modify_mofe_soils", lambda self: calls.append("modify_mofe_soils"))
    monkeypatch.setattr(Disturbed, "modify_soils", lambda self: calls.append("modify_soils"))

    disturbed.on(TriggerEvents.SOILS_BUILD_COMPLETE)

    assert calls == ["modify_mofe_soils"]


def test_on_routes_soils_event_to_single_ofe_when_multi_ofe_disabled(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("on-soils-single")
    landuse, soils = _controller_stubs()
    calls: list[str] = []

    monkeypatch.setattr(Disturbed, "wepp_instance", property(lambda self: SimpleNamespace(_multi_ofe=False)))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "modify_mofe_soils", lambda self: calls.append("modify_mofe_soils"))
    monkeypatch.setattr(Disturbed, "modify_soils", lambda self: calls.append("modify_soils"))

    disturbed.on(TriggerEvents.SOILS_BUILD_COMPLETE)

    assert calls == ["modify_soils"]
