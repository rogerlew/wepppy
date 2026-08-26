from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.project_config_serialization import (
    CanonicalConfigError,
    normalize_source_text,
    parse_config_text,
    serialize_config,
    validate_canonical_config_text,
)

pytestmark = pytest.mark.unit
REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_CONFIG = REPO_ROOT / "tests" / "data" / "project_config" / "canonical_v1.cfg"


def test_golden_bytes_are_sorted_and_stable() -> None:
    config = {
        "zeta": {"string": "snow", "nullable": None},
        "alpha": {"list": ["us", 30, True, None], "float": 10.0, "bool": False},
    }
    expected = GOLDEN_CONFIG.read_bytes()

    assert serialize_config(config) == expected
    assert serialize_config(parse_config_text(expected.decode())) == expected
    assert validate_canonical_config_text(expected.decode()) == parse_config_text(expected.decode())


def test_equivalent_maps_produce_identical_bytes() -> None:
    left = {"b": {"y": 2, "x": 1}, "a": {"value": "same"}}
    right = {"a": {"value": "same"}, "b": {"x": 1, "y": 2}}

    assert serialize_config(left) == serialize_config(right)


@pytest.mark.parametrize(
    "text",
    [
        "[a]\nx = 1\n[a]\ny = 2\n",
        "[a]\nx = 1\n[A]\ny = 2\n",
        "[a]\nx = 1\nx = 2\n",
        "[a]\nx = 1\nX = 2\n",
        "[a]\nx = bare\n",
        "[a]\nx = 1 # inline\n",
        "[a]\nx = nan\n",
        "[a]\nx\n",
        "[a]\nx = (1, 2)\n",
        "[a]\nx = [1,]\n",
    ],
)
def test_parser_rejects_ambiguous_or_unsupported_forms(text: str) -> None:
    with pytest.raises(CanonicalConfigError):
        parse_config_text(text)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_serializer_rejects_nonfinite_numbers(value: float) -> None:
    with pytest.raises(CanonicalConfigError, match="non-finite"):
        serialize_config({"section": {"value": value}})


def test_serializer_invokes_secret_materialization_gate() -> None:
    with pytest.raises(ValueError, match="secret-bearing option name"):
        serialize_config({"general": {"api_key": "unsafe"}})


def test_source_normalization_preserves_values_without_guessing_complex_types() -> None:
    source = "[general]\nflag = True\nname = bare\nitems = [\"us\",]\nvalue = 19 # rationale\n"
    expected = (
        "[general]\n"
        "flag = true\n"
        'name = "bare"\n'
        'items = ["us"]\n'
        "# rationale\n"
        "value = 19\n"
    )

    assert normalize_source_text(source) == expected


def test_source_normalization_converts_legacy_tuple_list() -> None:
    assert normalize_source_text("[general]\nlocales = ('eu',)\n") == '[general]\nlocales = ["eu"]\n'


@pytest.mark.parametrize(
    "source",
    [
        "[section]\nvalue = 1\n[section]\nother = 2\n",
        "[section]\nvalue = 1\n[Section]\nother = 2\n",
        "[section]\nvalue = 1\nvalue = 2\n",
        "[section]\nvalue = 1\nValue = 2\n",
    ],
)
def test_source_normalization_rejects_duplicate_and_case_collisions(source: str) -> None:
    with pytest.raises(CanonicalConfigError, match="duplicate or case-colliding"):
        normalize_source_text(source)


def test_active_source_corpus_is_lexically_normalized() -> None:
    config_root = REPO_ROOT / "wepppy" / "nodb" / "configs"
    paths = sorted(config_root.glob("*.cfg"))

    assert len(paths) == 129
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert normalize_source_text(source) == source, path
