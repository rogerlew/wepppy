import os
import stat
from pathlib import Path

import pytest

from wepppy.all_your_base.all_your_base import (
    RGBA,
    clamp,
    clamp01,
    cmyk_to_rgb,
    cp_chmod,
    find_ranges,
    flatten,
    isbool,
    isfloat,
    isinf,
    isint,
    isnan,
    parse_name,
    parse_units,
    splitall,
    try_parse,
    try_parse_float,
)
from wepppy.all_your_base.all_your_base import RowData


def test_rgba_fields_are_instance_specific() -> None:
    color_a = RGBA(10, 20, 30, 40)
    color_b = RGBA(200, 210, 220, 230)

    assert (color_a.red, color_a.green, color_a.blue, color_a.alpha) == (10, 20, 30, 40)
    assert (color_b.red, color_b.green, color_b.blue, color_b.alpha) == (200, 210, 220, 230)
    assert color_a != color_b


def test_rgba_is_immutable() -> None:
    color = RGBA(1, 2, 3, 4)

    with pytest.raises(AttributeError):
        setattr(color, "red", 10)

    with pytest.raises(TypeError):
        color[0] = 10  # type: ignore[index]


def test_cmyk_to_rgb_basic_conversion() -> None:
    assert cmyk_to_rgb(0.0, 0.0, 0.0, 0.0) == (1.0, 1.0, 1.0)
    r, g, b = cmyk_to_rgb(0.25, 0.10, 0.50, 0.20)
    assert pytest.approx((r, g, b), rel=1e-6) == (0.6, 0.72, 0.4)


def test_flatten_nested_iterables_respects_strings() -> None:
    nested = [1, [2, (3, [4])], "keep", b"bytes"]
    assert list(flatten(nested)) == [1, 2, 3, 4, "keep", b"bytes"]


def test_find_ranges_supports_list_and_string_output() -> None:
    values = [1, 2, 3, 5, 8, 9, 10]
    assert find_ranges(values) == [(1, 3), 5, (8, 10)]
    assert find_ranges(values, as_str=True) == "1-3, 5, 8-10"


def test_clamp_and_clamp01() -> None:
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10
    assert clamp01(-0.5) == 0.0
    assert clamp01(0.5) == 0.5
    assert clamp01(2.0) == 1.0


def test_cp_chmod_copies_and_sets_mode(tmp_path: Path) -> None:
    src = tmp_path / "source.txt"
    dst = tmp_path / "destination.txt"
    src.write_text("payload", encoding="utf-8")

    cp_chmod(str(src), str(dst), 0o640)

    assert dst.read_text(encoding="utf-8") == "payload"
    assert stat.S_IMODE(os.stat(dst).st_mode) == 0o640


def test_splitall_handles_absolute_and_relative_paths(tmp_path: Path) -> None:
    absolute = tmp_path / "nested" / "file.txt"
    absolute.parent.mkdir()
    absolute.touch()
    parts = splitall(str(absolute))
    assert parts[-2:] == ["nested", "file.txt"]

    relative_parts = splitall("a/b/c")
    assert relative_parts == ["a", "b", "c"]


def test_numeric_predicates_and_parsers() -> None:
    assert isint("10")
    assert not isint("10.5")
    assert isfloat("10.5")
    assert not isfloat("ten")
    assert isbool(True)
    assert isbool(0)
    assert not isbool("yes")
    assert isnan(float("nan"))
    assert not isnan("value")
    assert isinf(float("inf"))
    assert not isinf(100)
    assert try_parse("4") == 4
    assert try_parse("4.2") == 4.2
    assert try_parse("value") == "value"
    assert try_parse_float("missing", default=1.23) == 1.23


def test_parse_name_units_and_rowdata_iteration() -> None:
    colname = "Streamflow (m3/s)"
    assert parse_units(colname) == "m3/s"
    assert parse_name(colname) == "Streamflow"

    row = RowData({"Streamflow (m3/s)": 42, "precip": 1.2})
    assert row["Streamflow"] == 42
    assert list(row) == [(42, "m3/s"), (1.2, None)]
    with pytest.raises(KeyError):
        _ = row["missing"]
