from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from wepppy.nodb.core.landuse import Landuse
from wepppy.wepp.management import InvalidManagementKey

pytestmark = pytest.mark.unit


def _landuse_for_modify() -> Landuse:
    landuse = Landuse.__new__(Landuse)
    landuse.domlc_d = {'101': '90', '102': '90'}
    landuse.domlc_mofe_d = {
        '101': {'1': '90', '2': '90'},
        '102': {'1': '90', '2': '70'},
    }
    landuse.managements = {'90': object(), '70': object()}
    landuse._mapping = 'mock-map'
    landuse.cover_defaults_d = None
    landuse.locked = lambda: nullcontext()
    return landuse


def test_modify_regenerates_mofe_assignments_and_managements(monkeypatch: pytest.MonkeyPatch) -> None:
    landuse = _landuse_for_modify()
    monkeypatch.setattr(Landuse, 'multi_ofe', property(lambda _self: True))
    monkeypatch.setattr(
        Landuse,
        'watershed_instance',
        property(lambda _self: SimpleNamespace(mofe_nsegments={'101': 2, '102': 2})),
    )
    monkeypatch.setattr('wepppy.nodb.core.landuse.get_management_summary', lambda *_args: object())

    captured: list[dict[str, dict[str, str]]] = []
    summary_rebuilds: list[dict[str, object]] = []

    def _rebuild_mofe(*, domlc_mofe_override: dict[str, dict[str, str]]) -> None:
        captured.append(domlc_mofe_override)
        landuse.managements['424'] = object()

    landuse._build_multiple_ofe = _rebuild_mofe
    landuse.build_managements = lambda: summary_rebuilds.append(landuse.managements)
    landuse.set_cover_defaults = lambda: None

    landuse.modify(['101'], '424')

    assert landuse.domlc_d == {'101': '424', '102': '90'}
    assert landuse.domlc_mofe_d == {
        '101': {'1': '424', '2': '424'},
        '102': {'1': '90', '2': '70'},
    }
    assert captured == [landuse.domlc_mofe_d]
    assert summary_rebuilds == [landuse.managements]
    assert '424' in summary_rebuilds[0]


def test_modify_rejects_unbuilt_mofe_state(monkeypatch: pytest.MonkeyPatch) -> None:
    landuse = _landuse_for_modify()
    landuse.domlc_mofe_d = None
    monkeypatch.setattr(Landuse, 'multi_ofe', property(lambda _self: True))
    monkeypatch.setattr('wepppy.nodb.core.landuse.get_management_summary', lambda *_args: object())

    with pytest.raises(ValueError, match='build landuse before modifying'):
        landuse.modify(['101'], '424')

    assert landuse.domlc_d == {'101': '90', '102': '90'}


def test_modify_rejects_unknown_class_before_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    landuse = _landuse_for_modify()
    monkeypatch.setattr(Landuse, 'multi_ofe', property(lambda _self: True))

    def _unknown_class(*_args: object) -> object:
        raise InvalidManagementKey('unknown')

    monkeypatch.setattr('wepppy.nodb.core.landuse.get_management_summary', _unknown_class)

    with pytest.raises(ValueError, match='Unknown landuse class: 999'):
        landuse.modify(['101'], '999')

    assert landuse.domlc_d == {'101': '90', '102': '90'}
    assert landuse.domlc_mofe_d['101']['1'] == '90'


def test_modify_rejects_incomplete_mofe_state_before_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    landuse = _landuse_for_modify()
    landuse.domlc_mofe_d['102'].pop('2')
    monkeypatch.setattr(Landuse, 'multi_ofe', property(lambda _self: True))
    monkeypatch.setattr(
        Landuse,
        'watershed_instance',
        property(lambda _self: SimpleNamespace(mofe_nsegments={'101': 2, '102': 2})),
    )
    monkeypatch.setattr('wepppy.nodb.core.landuse.get_management_summary', lambda *_args: object())

    with pytest.raises(ValueError, match='incomplete OFE segments'):
        landuse.modify(['101'], '424')

    assert landuse.domlc_d == {'101': '90', '102': '90'}


def test_modify_rejects_unknown_selection_before_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    landuse = _landuse_for_modify()
    monkeypatch.setattr(Landuse, 'multi_ofe', property(lambda _self: False))
    monkeypatch.setattr('wepppy.nodb.core.landuse.get_management_summary', lambda *_args: object())

    with pytest.raises(ValueError, match='missing for Topaz ID'):
        landuse.modify(['101', 'missing'], '424')

    assert landuse.domlc_d == {'101': '90', '102': '90'}


def test_modify_rejects_nonsequential_mofe_ids_before_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    landuse = _landuse_for_modify()
    landuse.domlc_mofe_d['102'] = {'1': '90', '3': '70'}
    monkeypatch.setattr(Landuse, 'multi_ofe', property(lambda _self: True))
    monkeypatch.setattr(
        Landuse,
        'watershed_instance',
        property(lambda _self: SimpleNamespace(mofe_nsegments={'101': 2, '102': 2})),
    )
    monkeypatch.setattr('wepppy.nodb.core.landuse.get_management_summary', lambda *_args: object())

    with pytest.raises(ValueError, match='incomplete OFE segments'):
        landuse.modify(['101'], '424')

    assert landuse.domlc_d == {'101': '90', '102': '90'}
