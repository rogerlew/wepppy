import re
from pathlib import Path

from wepppy.nodb.mods.baer.sbs_map import SBS_DISPLAY_CLASSES, SBS_UNASSIGNED_RGBA


REPO_ROOT = Path(__file__).resolve().parents[4]
CLIENT_SOURCES = (
    REPO_ROOT / "wepppy/weppcloud/controllers_js/map_gl_shared.js",
    REPO_ROOT / "wepppy/weppcloud/static/js/gl-dashboard/map/layers.js",
)
CLASS_PATTERN = re.compile(
    r"(13[0-3]):[^\n]*label:\s*['\"]([^'\"]+)['\"][^\n]*"
    r"standard:\s*\[([0-9, ]+)\][^\n]*shifted:\s*\[([0-9, ]+)\]"
)
DECODE_PATTERN = re.compile(r"['\"](\d+_\d+_\d+)['\"]:\s*(13[0-3])")
SENTINEL_PATTERN = re.compile(r"SBS_UNASSIGNED_RGB[^=]*=\s*(?:Object\.freeze\()?\[([0-9, ]+)\]")


def _client_contract(path: Path):
    source = path.read_text(encoding="utf-8")
    classes = {
        int(code): (
            label,
            tuple(int(value) for value in standard.split(",")),
            tuple(int(value) for value in shifted.split(",")),
        )
        for code, label, standard, shifted in CLASS_PATTERN.findall(source)
    }
    decode = {rgb: int(code) for rgb, code in DECODE_PATTERN.findall(source)}
    sentinel_match = SENTINEL_PATTERN.search(source)
    assert sentinel_match is not None
    sentinel = tuple(int(value) for value in sentinel_match.group(1).split(","))
    return classes, decode, sentinel


def test_sbs_class_contract_stays_in_parity_across_python_and_clients():
    shifted = {
        130: (0, 158, 115),
        131: (86, 180, 233),
        132: (240, 228, 66),
        133: (204, 121, 167),
    }
    expected_classes = {
        code: (label, tuple(bytes.fromhex(color.removeprefix("#"))), shifted[code])
        for code, label, color in SBS_DISPLAY_CLASSES
        if code != 255
    }
    run_page = _client_contract(CLIENT_SOURCES[0])
    dashboard = _client_contract(CLIENT_SOURCES[1])

    assert run_page == dashboard
    assert run_page[0] == expected_classes
    assert run_page[2] == SBS_UNASSIGNED_RGBA[:3]
    assert set(run_page[1].values()) == set(expected_classes)
    assert len(run_page[1]) == 12
