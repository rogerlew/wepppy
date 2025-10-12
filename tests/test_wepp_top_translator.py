import importlib.util
import sys
from pathlib import Path
from typing import Dict, List

import pytest


_MODULE_PATH = Path(__file__).resolve().parents[1] / "wepppy/topo/watershed_abstraction/wepp_top_translator.py"
_SPEC = importlib.util.spec_from_file_location(
    "wepppy.topo.watershed_abstraction.wepp_top_translator",
    _MODULE_PATH,
)
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault(_SPEC.name, _MODULE)
assert _SPEC.loader is not None  # for mypy
_SPEC.loader.exec_module(_MODULE)

WeppTopTranslator = _MODULE.WeppTopTranslator
upland_hillslopes = _MODULE.upland_hillslopes


@pytest.fixture
def translator() -> WeppTopTranslator:
    return WeppTopTranslator(
        top_sub_ids=[103, 101, 102],
        top_chn_ids=[104, 204],
    )


@pytest.fixture
def simple_network() -> Dict[int, List[int]]:
    return {
        204: [104],
        104: [],
    }


def test_translator_orders_ids(translator: WeppTopTranslator) -> None:
    assert list(translator.iter_sub_ids()) == ["hill_101", "hill_102", "hill_103"]
    assert list(translator.iter_chn_ids()) == ["chn_204", "chn_104"]
    assert list(translator) == [101, 102, 103, 204, 104]


@pytest.mark.parametrize(
    ("top_id", "wepp_id"),
    [
        (101, 1),
        (102, 2),
        (103, 3),
        (204, 4),
        (104, 5),
    ],
)
def test_top_wepp_roundtrip(translator: WeppTopTranslator, top_id: int, wepp_id: int) -> None:
    assert translator.top(wepp=wepp_id) == top_id
    assert translator.wepp(top=top_id) == wepp_id


def test_sub_and_channel_identifier_resolution(translator: WeppTopTranslator) -> None:
    assert translator.wepp(sub_id="hill_101") == 1
    assert translator.wepp(sub_id="101") == 1
    assert translator.top(sub_id="hill_102") == 102
    assert translator.wepp(chn_id="chn_204") == 4
    assert translator.top(chn_id="chn_104") == 104


def test_channel_enum_and_flags(translator: WeppTopTranslator) -> None:
    assert translator.chn_enum(chn_id="chn_204") == 1
    assert translator.chn_enum(chn_id="chn_104") == 2
    assert translator.chn_enum(wepp=4) == 1
    assert translator.chn_enum(top=104) == 2
    assert translator.is_channel(top=204) is True
    assert translator.is_channel(wepp=5) is True
    assert translator.is_channel(top=101) is False
    assert translator.has_top(101) is True
    assert translator.has_top(999) is False


def test_channel_hillslopes(translator: WeppTopTranslator) -> None:
    assert translator.channel_hillslopes("chn_104") == [102, 103, 101]
    assert translator.channel_hillslopes(104) == [102, 103, 101]


def test_iterators(translator: WeppTopTranslator) -> None:
    assert list(translator.iter_wepp_sub_ids()) == [1, 2, 3]
    assert list(translator.iter_wepp_chn_ids()) == [4, 5]


def test_build_structure(translator: WeppTopTranslator, simple_network: Dict[int, List[int]]) -> None:
    assert translator.build_structure(simple_network) == [
        [1, 0, 0, 0, 104, 0, 0, 0, 0, 0],
        [2, 102, 103, 101, 0, 0, 0, 0, 0, 0],
    ]


def test_upland_hillslopes(translator: WeppTopTranslator, simple_network: Dict[int, List[int]]) -> None:
    assert upland_hillslopes(104, simple_network, translator) == [102, 103, 101]
    assert upland_hillslopes(204, simple_network, translator) == [102, 103, 101]
