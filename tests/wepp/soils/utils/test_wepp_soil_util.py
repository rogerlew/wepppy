import uuid
import sys
import types
import importlib.util
from pathlib import Path

import yaml as pyyaml

if "oyaml" not in sys.modules:
    sys.modules["oyaml"] = pyyaml

if "deprecated" not in sys.modules:
    deprecated_stub = types.ModuleType("deprecated")

    def _deprecated(*d_args, **d_kwargs):
        if d_args and callable(d_args[0]) and not d_kwargs:
            return d_args[0]

        def _decorator(func):
            return func

        return _decorator

    deprecated_stub.deprecated = _deprecated
    sys.modules["deprecated"] = deprecated_stub

REPO_ROOT = Path(__file__).resolve().parents[4]
WEPP_SOIL_UTIL_PATH = (
    REPO_ROOT / "wepppy" / "wepp" / "soils" / "utils" / "wepp_soil_util.py"
)


def _ensure_package(name: str, path: Path):
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module


_ensure_package("wepppy", REPO_ROOT / "wepppy")
_ensure_package("wepppy.wepp", REPO_ROOT / "wepppy" / "wepp")
_ensure_package("wepppy.wepp.soils", REPO_ROOT / "wepppy" / "wepp" / "soils")
_ensure_package(
    "wepppy.wepp.soils.utils", REPO_ROOT / "wepppy" / "wepp" / "soils" / "utils"
)


all_your_base_stub = types.ModuleType("wepppy.all_your_base")


def _stub_try_parse(value):
    if isinstance(value, (int, float)):
        return value
    try:
        as_float = float(value)
    except Exception:
        return value
    try:
        as_int = int(value)
        return as_int
    except Exception:
        return as_float


def _stub_try_parse_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _stub_isfloat(value):
    try:
        float(value)
        return True
    except Exception:
        return False


all_your_base_stub.try_parse = _stub_try_parse
all_your_base_stub.try_parse_float = _stub_try_parse_float
all_your_base_stub.isfloat = _stub_isfloat
sys.modules["wepppy.all_your_base"] = all_your_base_stub


module_spec = importlib.util.spec_from_file_location(
    "wepppy.wepp.soils.utils.wepp_soil_util", WEPP_SOIL_UTIL_PATH
)
module = importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name] = module
module_spec.loader.exec_module(module)

import oyaml as yaml
import pytest

WeppSoilUtil = module.WeppSoilUtil
_replace_parameter = module._replace_parameter
_pars_to_string = module._pars_to_string

from wepppy.wepp.soils.utils.wepp_soil_util import (
    WeppSoilUtil,
    _replace_parameter,
    _pars_to_string,
)


def _soil_payload(luse="test use"):
    return {
        "header": ["initial header"],
        "datver": 7778.0,
        "solcom": "example solcom",
        "ntemp": 1,
        "ksflag": 1,
        "ofes": [
            {
                "slid": "SLID",
                "texid": "TEX",
                "nsl": 2,
                "salb": 0.1,
                "sat": 0.5,
                "ki": "1",
                "kr": "2",
                "shcrit": "3",
                "avke": "4",
                "horizons": [
                    {
                        "solthk": 50.0,
                        "bd": 1.2,
                        "ksat": 0.1,
                        "anisotropy": 1.0,
                        "fc": 0.3,
                        "wp": 0.1,
                        "sand": 60.0,
                        "clay": 20.0,
                        "orgmat": 1.0,
                        "cec": 10.0,
                        "rfg": 0.0,
                    },
                    {
                        "solthk": 250.0,
                        "bd": 1.3,
                        "ksat": 0.2,
                        "anisotropy": 1.0,
                        "fc": 0.35,
                        "wp": 0.12,
                        "sand": 55.0,
                        "clay": 25.0,
                        "orgmat": 1.2,
                        "cec": 11.0,
                        "rfg": 0.0,
                    },
                ],
                "ksatadj": "1",
                "luse": luse,
                "stext": "some text",
                "uksat": "-9999",
                "texid_enum": None,
                "lkeff": "-9999",
                "ksatfac": "1",
                "ksatrec": "1",
                "res_lyr": {"slflag": 1, "ui_bdrkth": 100.0, "kslast": 0.5},
            }
        ],
        "res_lyr": {"slflag": 1, "ui_bdrkth": 100.0, "kslast": 0.5},
    }


@pytest.fixture
def workspace_tmp_dir():
    base = Path(__file__).parent / "__tmp__"
    base.mkdir(parents=True, exist_ok=True)
    tmp_dir = base / uuid.uuid4().hex
    tmp_dir.mkdir()
    yield tmp_dir
    for child in tmp_dir.iterdir():
        child.unlink()
    tmp_dir.rmdir()


@pytest.fixture
def make_soil_yaml(workspace_tmp_dir):
    def _factory(luse="test use"):
        payload = _soil_payload(luse=luse)
        path = workspace_tmp_dir / f"soil_{uuid.uuid4().hex}.yaml"
        path.write_text(yaml.dump(payload))
        return path

    return _factory


def test_replace_parameter_with_multiplier():
    assert _replace_parameter("10", "*2") == "20.0"


def test_replace_parameter_with_none_like_string():
    assert _replace_parameter("10", "None") == "10"
    assert _replace_parameter("10", " none ") == "10"


def test_pars_to_string_formats_values():
    formatted = _pars_to_string({"a": "value", "b": 1.5})
    assert formatted == "(a='value', b=1.5)"


def test_modify_initial_sat_updates_all_ofes_and_header(make_soil_yaml):
    path = make_soil_yaml()
    util = WeppSoilUtil(str(path))

    util.modify_initial_sat(0.9)

    assert util.obj["ofes"][0]["sat"] == 0.9
    assert (
        util.obj["header"][-1]
        == "wepppy.wepp.soils.utils.WeppSoilUtil::modify_initial_sat(initial_sat=0.9)"
    )


def test_modify_kslast_skips_developed_soils(make_soil_yaml):
    path = make_soil_yaml(luse="Highly Developed area")
    util = WeppSoilUtil(str(path))
    original_header = list(util.obj["header"])
    original_kslast = util.obj["ofes"][0]["res_lyr"]["kslast"]

    util.modify_kslast(1.2)

    assert util.obj["header"] == original_header
    assert util.obj["ofes"][0]["res_lyr"]["kslast"] == original_kslast
    assert util.obj["res_lyr"]["kslast"] == original_kslast


def test_modify_kslast_updates_soil_and_header(make_soil_yaml):
    path = make_soil_yaml()
    util = WeppSoilUtil(str(path))

    util.modify_kslast(1.8, pars={"reason": "adjusted"})

    assert util.obj["ofes"][0]["res_lyr"]["kslast"] == 1.8
    assert util.obj["res_lyr"]["kslast"] == 1.8
    assert (
        util.obj["header"][-1]
        == "wepppy.wepp.soils.utils.WeppSoilUtil::modify_kslast(reason='adjusted')"
    )


def test_clip_soil_depth_truncates_horizons(make_soil_yaml):
    path = make_soil_yaml()
    util = WeppSoilUtil(str(path))

    util.clip_soil_depth(120)

    horizons = util.obj["ofes"][0]["horizons"]
    assert len(horizons) == 2
    assert horizons[-1]["solthk"] == 120
    assert util.obj["ofes"][0]["nsl"] == 2
    assert (
        util.obj["header"][-1]
        == "wepppy.wepp.soils.utils.WeppSoilUtil::clip_soil_depth(max_depth=120)"
    )


def test_dump_yaml_round_trip(workspace_tmp_dir):
    payload = _soil_payload()
    src = workspace_tmp_dir / "source.yaml"
    src.write_text(yaml.dump(payload))
    util = WeppSoilUtil(str(src))

    dst = workspace_tmp_dir / "round_trip.yaml"
    util.dump_yaml(str(dst))

    round_trip = yaml.safe_load(dst.read_text())
    assert round_trip == util.obj
