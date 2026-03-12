from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path

import pytest

from wepppy.nodb.core.wepp import BaseflowOpts, Wepp

pytestmark = pytest.mark.unit


def _new_wepp_for_baseflow_tests(tmp_path: Path, logger_name: str) -> Wepp:
    wepp = Wepp.__new__(Wepp)
    wepp.wd = str(tmp_path)
    wepp.logger = logging.getLogger(logger_name)
    wepp._logger = wepp.logger
    wepp.config_get_float = lambda _section, _option, default=None: default  # type: ignore[assignment]
    wepp.config_get_int = lambda _section, _option, default=None: default  # type: ignore[assignment]
    return wepp


def test_baseflow_opts_parse_inputs_accepts_prefixed_keys() -> None:
    opts = BaseflowOpts()

    opts.parse_inputs(
        {
            "baseflow_opts_gwstorage": "250.0",
            "baseflow_opts_bfcoeff": "0.07",
            "baseflow_opts_dscoeff": "0.01",
            "baseflow_opts_bfthreshold": "2.5",
        }
    )

    assert opts.gwstorage == pytest.approx(250.0)
    assert opts.bfcoeff == pytest.approx(0.07)
    assert opts.dscoeff == pytest.approx(0.01)
    assert opts.bfthreshold == pytest.approx(2.5)


@pytest.mark.parametrize("bfcoeff", [0.07, 0.1])
def test_guard_unitized_bounds_keeps_supported_baseflow_coefficients(
    tmp_path: Path, bfcoeff: float
) -> None:
    wepp = _new_wepp_for_baseflow_tests(tmp_path, "tests.wepp.baseflow.guard_valid")
    wepp.baseflow_opts = BaseflowOpts(bfcoeff=bfcoeff)

    wepp._guard_unitized_bounds()

    assert wepp.baseflow_opts.bfcoeff == pytest.approx(bfcoeff)


@pytest.mark.parametrize("bfcoeff", [0.005, 0.11, float("nan"), float("inf")])
def test_guard_unitized_bounds_resets_invalid_baseflow_coefficients_to_default(
    tmp_path: Path, bfcoeff: float
) -> None:
    wepp = _new_wepp_for_baseflow_tests(tmp_path, "tests.wepp.baseflow.guard_default")
    wepp.baseflow_opts = BaseflowOpts(bfcoeff=bfcoeff)

    wepp._guard_unitized_bounds()

    assert wepp.baseflow_opts.bfcoeff == pytest.approx(0.04)


def test_set_baseflow_opts_applies_baseflow_coefficient_bounds(tmp_path: Path) -> None:
    wepp = _new_wepp_for_baseflow_tests(tmp_path, "tests.wepp.baseflow.setter")

    @contextmanager
    def _fake_locked():
        yield

    wepp.locked = _fake_locked  # type: ignore[assignment]

    wepp.set_baseflow_opts(bfcoeff=0.11)

    assert wepp.baseflow_opts.bfcoeff == pytest.approx(0.04)
