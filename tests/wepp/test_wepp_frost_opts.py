from __future__ import annotations

import logging
from pathlib import Path

import pytest

from wepppy.nodb.core.wepp import FrostOpts, Wepp

pytestmark = pytest.mark.unit


def _token_counts(text: str) -> tuple[int, int]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    assert len(lines) == 2
    return len(lines[0].split()), len(lines[1].split())


def _new_wepp_for_frost_tests(tmp_path: Path, logger_name: str) -> Wepp:
    wepp = Wepp.__new__(Wepp)
    wepp.wd = str(tmp_path)
    wepp.logger = logging.getLogger(logger_name)
    wepp._logger = wepp.logger
    wepp.config_get_int = lambda _section, _option, default=None: default  # type: ignore[assignment]
    wepp.config_get_float = lambda _section, _option, default=None: default  # type: ignore[assignment]
    return wepp


def test_frost_opts_default_contents_match_wepp_file_shape() -> None:
    opts = FrostOpts()

    top_tokens, bottom_tokens = _token_counts(opts.contents)

    assert top_tokens == 3
    assert bottom_tokens == 6
    assert opts.wintRed == 1
    assert opts.fineTop == 10
    assert opts.fineBot == 10
    assert opts.kfactor1 == pytest.approx(1e-5)
    assert opts.kfactor2 == pytest.approx(1e-5)
    assert opts.kfactor3 == pytest.approx(0.5)


def test_frost_opts_contents_preserves_second_line_value_order() -> None:
    opts = FrostOpts(
        ksnowf=1.5,
        kresf=1.25,
        ksoilf=0.75,
        kfactor1=0.01,
        kfactor2=0.02,
        kfactor3=0.5,
    )
    lines = [line.strip() for line in opts.contents.splitlines() if line.strip()]
    second_line_values = [float(token) for token in lines[1].split()]
    assert second_line_values == pytest.approx([1.5, 1.25, 0.75, 0.01, 0.02, 0.5])


def test_frost_opts_parse_inputs_accepts_prefixed_keys() -> None:
    opts = FrostOpts()
    opts.parse_inputs(
        {
            "frost_opts_wintRed": "0",
            "frost_opts_fineTop": "8",
            "frost_opts_fineBot": "6",
            "frost_opts_ksnowf": "1.5",
            "frost_opts_kresf": "1.25",
            "frost_opts_ksoilf": "0.75",
            "frost_opts_kfactor1": "0.01",
            "frost_opts_kfactor2": "0.02",
            "frost_opts_kfactor3": "0.5",
        }
    )

    assert opts.wintRed == 0
    assert opts.fineTop == 8
    assert opts.fineBot == 6
    assert opts.ksnowf == pytest.approx(1.5)
    assert opts.kresf == pytest.approx(1.25)
    assert opts.ksoilf == pytest.approx(0.75)
    assert opts.kfactor1 == pytest.approx(0.01)
    assert opts.kfactor2 == pytest.approx(0.02)
    assert opts.kfactor3 == pytest.approx(0.5)


def test_prep_frost_writes_two_line_compliant_file(tmp_path: Path) -> None:
    wepp = _new_wepp_for_frost_tests(tmp_path, "tests.wepp.frost.prep")
    wepp.frost_opts = FrostOpts()

    Path(wepp.runs_dir).mkdir(parents=True, exist_ok=True)
    wepp._prep_frost()

    frost_path = Path(wepp.runs_dir) / "frost.txt"
    assert frost_path.exists()
    top_tokens, bottom_tokens = _token_counts(frost_path.read_text())
    assert top_tokens == 3
    assert bottom_tokens == 6


def test_mint_default_frost_file_is_idempotent(tmp_path: Path) -> None:
    wepp = _new_wepp_for_frost_tests(tmp_path, "tests.wepp.frost.mint")
    wepp.frost_opts = FrostOpts()

    wepp._mint_default_frost_file()
    frost_path = Path(wepp.runs_dir) / "frost.txt"
    assert frost_path.exists()
    original = frost_path.read_text()
    assert _token_counts(original) == (3, 6)

    frost_path.write_text("sentinel\n")
    wepp._mint_default_frost_file()
    assert frost_path.read_text() == "sentinel\n"


def test_guard_frost_bounds_resets_invalid_values_to_wepp_defaults(tmp_path: Path) -> None:
    wepp = _new_wepp_for_frost_tests(tmp_path, "tests.wepp.frost.guard_defaults")
    wepp.frost_opts = FrostOpts(
        wintRed=2,
        fineTop=11,
        fineBot=0,
        ksnowf=float("nan"),
        kresf=float("inf"),
        ksoilf=0.05,
        kfactor1=0.0,
        kfactor2=-0.1,
        kfactor3=2.0,
    )

    wepp._guard_frost_bounds()

    assert wepp.frost_opts.wintRed == 1
    assert wepp.frost_opts.fineTop == 10
    assert wepp.frost_opts.fineBot == 10
    assert wepp.frost_opts.ksnowf == pytest.approx(1.0)
    assert wepp.frost_opts.kresf == pytest.approx(1.0)
    assert wepp.frost_opts.ksoilf == pytest.approx(1.0)
    assert wepp.frost_opts.kfactor1 == pytest.approx(1e-5)
    assert wepp.frost_opts.kfactor2 == pytest.approx(1e-5)
    assert wepp.frost_opts.kfactor3 == pytest.approx(0.5)


def test_guard_frost_bounds_keeps_tiny_positive_kfactor_values(tmp_path: Path) -> None:
    wepp = _new_wepp_for_frost_tests(tmp_path, "tests.wepp.frost.guard_positive")
    tiny = 1e-20
    wepp.frost_opts = FrostOpts(kfactor1=tiny, kfactor2=tiny, kfactor3=tiny)

    wepp._guard_frost_bounds()

    assert wepp.frost_opts.kfactor1 == pytest.approx(tiny)
    assert wepp.frost_opts.kfactor2 == pytest.approx(tiny)
    assert wepp.frost_opts.kfactor3 == pytest.approx(tiny)
