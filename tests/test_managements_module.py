import importlib.util
import shutil
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def managements_module():
    """
    Load the `wepppy.wepp.management.managements` module without triggering the
    heavy `wepppy.wepp` package import side effects.
    """
    repo_root = Path(__file__).resolve().parent.parent
    package_root = repo_root / "wepppy"

    created_modules: dict[str, None] = {}

    def ensure_package(name: str, path: Path) -> None:
        if name in sys.modules:
            return
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module
        created_modules[name] = None

    ensure_package("wepppy", package_root)
    ensure_package("wepppy.wepp", package_root / "wepp")
    ensure_package("wepppy.wepp.management", package_root / "wepp/management")

    spec = importlib.util.spec_from_file_location(
        "wepppy.wepp.management.managements",
        package_root / "wepp/management/managements.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["wepppy.wepp.management.managements"] = module
    created_modules["wepppy.wepp.management.managements"] = None
    assert spec.loader is not None
    spec.loader.exec_module(module)

    try:
        yield module
    finally:
        for name in list(created_modules):
            sys.modules.pop(name, None)


def test_get_management_basic_metadata(managements_module):
    man = managements_module.get_management(21)

    assert man.man_fn == "GeoWEPP/grass.man"
    assert man.nofe == 1
    assert man.sim_years == 1
    assert man.plants[0].name == "bromegr1"
    assert man.inis[0].data.cancov == pytest.approx(0.5)


def test_operations_report_cli_no_operations(managements_module):
    man = managements_module.get_management(21)

    assert man.operations_report() == []
    assert man.operations_report_cli() == "No operations scheduled."


def test_read_management_uses_provided_path(managements_module):
    data_dir = Path(managements_module._management_dir)
    man_path = data_dir / "GeoWEPP" / "grass.man"

    read_man = managements_module.read_management(str(man_path))

    assert read_man.man_dir == str(man_path.parent)
    assert read_man.man_fn == "grass.man"
    assert read_man.plants[0].name == "bromegr1"


def test_get_channel_management_metadata(managements_module):
    channel = managements_module.get_channel_management()

    assert channel.man_fn == "channel.man"
    assert channel.desc == "Channel"
    assert channel.color == (0, 0, 255, 255)
    assert channel.nofe == 1


def test_get_plant_loop_names_ignores_pw0(tmp_path, managements_module):
    data_dir = Path(managements_module._management_dir)
    source = data_dir / "GeoWEPP" / "grass.man"

    target = tmp_path / "copy.man"
    shutil.copy(source, target)
    shutil.copy(source, tmp_path / "ignored_pw0.man")

    plant_loops = managements_module.get_plant_loop_names(str(tmp_path))

    assert set(plant_loops) == {"bromegr1"}
