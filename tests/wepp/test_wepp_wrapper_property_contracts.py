from __future__ import annotations

from random import Random
from pathlib import Path

import pytest

from wepppy.nodb.core.wepp import (
    BaseflowOpts,
    FrostOpts,
    PhosphorusOpts,
    validate_phosphorus_txt,
)

pytestmark = pytest.mark.unit


def _generated_frost_payloads() -> list[dict[str, str]]:
    rng = Random(20260421)
    payloads: list[dict[str, str]] = []
    for _ in range(18):
        payloads.append(
            {
                "wintRed": str(rng.choice((0, 1))),
                "fineTop": str(rng.randint(1, 10)),
                "fineBot": str(rng.randint(1, 10)),
                "ksnowf": f"{rng.uniform(0.1, 10.0):.6f}",
                "kresf": f"{rng.uniform(0.1, 10.0):.6f}",
                "ksoilf": f"{rng.uniform(0.1, 10.0):.6f}",
                "kfactor1": f"{rng.uniform(1e-8, 1.0):.8f}",
                "kfactor2": f"{rng.uniform(1e-8, 1.0):.8f}",
                "kfactor3": f"{rng.uniform(1e-8, 1.0):.8f}",
            }
        )
    return payloads


def _generated_baseflow_payloads() -> list[dict[str, str]]:
    rng = Random(20260422)
    payloads: list[dict[str, str]] = []
    for _ in range(18):
        payloads.append(
            {
                "gwstorage": f"{rng.uniform(0.0, 500.0):.6f}",
                "bfcoeff": f"{rng.uniform(0.01, 0.1):.8f}",
                "dscoeff": f"{rng.uniform(0.0, 0.2):.8f}",
                "bfthreshold": f"{rng.uniform(0.1, 20.0):.6f}",
            }
        )
    return payloads


def _generated_phosphorus_payloads() -> list[dict[str, str]]:
    rng = Random(20260423)
    payloads: list[dict[str, str]] = []
    for _ in range(18):
        payloads.append(
            {
                "surf_runoff": f"{rng.uniform(0.001, 20.0):.6f}",
                "lateral_flow": f"{rng.uniform(0.001, 20.0):.6f}",
                "baseflow": f"{rng.uniform(0.001, 20.0):.6f}",
                "sediment": f"{rng.uniform(0.001, 5000.0):.6f}",
            }
        )
    return payloads


def _parse_frost_contents(contents: str) -> dict[str, str]:
    lines = [line.strip() for line in contents.splitlines() if line.strip()]
    assert len(lines) == 2

    top_tokens = lines[0].split()
    lower_tokens = lines[1].split()
    assert len(top_tokens) == 3
    assert len(lower_tokens) == 6

    return {
        "wintRed": top_tokens[0],
        "fineTop": top_tokens[1],
        "fineBot": top_tokens[2],
        "ksnowf": lower_tokens[0],
        "kresf": lower_tokens[1],
        "ksoilf": lower_tokens[2],
        "kfactor1": lower_tokens[3],
        "kfactor2": lower_tokens[4],
        "kfactor3": lower_tokens[5],
    }


def _parse_baseflow_contents(contents: str) -> dict[str, str]:
    lines = [line.strip() for line in contents.splitlines() if line.strip()]
    assert len(lines) == 4
    tokens = [line.split("\t", 1)[0].strip() for line in lines]
    return {
        "gwstorage": tokens[0],
        "bfcoeff": tokens[1],
        "dscoeff": tokens[2],
        "bfthreshold": tokens[3],
    }


def _parse_phosphorus_contents(contents: str) -> dict[str, str]:
    lines = [line.strip() for line in contents.splitlines() if line.strip()]
    assert lines[0] == "Phosphorus concentration"
    assert len(lines) == 5
    tokens = [line.split("\t", 1)[0].strip() for line in lines[1:]]
    return {
        "surf_runoff": tokens[0],
        "lateral_flow": tokens[1],
        "baseflow": tokens[2],
        "sediment": tokens[3],
    }


@pytest.mark.parametrize("payload", _generated_frost_payloads())
def test_frost_opts_round_trip_and_schema_invariants(payload: dict[str, str]) -> None:
    parsed = FrostOpts()
    parsed.parse_inputs({f"frost_opts_{key}": value for key, value in payload.items()})

    serialized = parsed.contents
    round_trip_payload = _parse_frost_contents(serialized)

    clone = FrostOpts()
    clone.parse_inputs(round_trip_payload)

    assert clone.contents == serialized


@pytest.mark.parametrize("payload", _generated_baseflow_payloads())
def test_baseflow_opts_round_trip_and_schema_invariants(payload: dict[str, str]) -> None:
    parsed = BaseflowOpts()
    parsed.parse_inputs({f"baseflow_opts_{key}": value for key, value in payload.items()})

    serialized = parsed.contents
    round_trip_payload = _parse_baseflow_contents(serialized)

    clone = BaseflowOpts()
    clone.parse_inputs(round_trip_payload)

    assert clone.contents == serialized


@pytest.mark.parametrize("payload", _generated_phosphorus_payloads())
def test_phosphorus_opts_round_trip_and_schema_invariants(payload: dict[str, str]) -> None:
    parsed = PhosphorusOpts()
    parsed.parse_inputs({f"phosphorus_opts_{key}": value for key, value in payload.items()})
    assert parsed.isvalid

    serialized = parsed.contents
    round_trip_payload = _parse_phosphorus_contents(serialized)

    clone = PhosphorusOpts()
    clone.parse_inputs(round_trip_payload)

    assert clone.contents == serialized


def test_wrapper_serialization_is_deterministic_for_equivalent_canonical_payloads() -> None:
    for frost_payload in _generated_frost_payloads():
        direct = FrostOpts()
        direct.parse_inputs(frost_payload)

        prefixed = FrostOpts()
        prefixed.parse_inputs(
            {f"frost_opts_{key}": value for key, value in frost_payload.items()}
        )

        assert prefixed.contents == direct.contents

    for baseflow_payload in _generated_baseflow_payloads():
        direct = BaseflowOpts()
        direct.parse_inputs(baseflow_payload)

        prefixed = BaseflowOpts()
        prefixed.parse_inputs(
            {f"baseflow_opts_{key}": value for key, value in baseflow_payload.items()}
        )

        assert prefixed.contents == direct.contents

    for phosphorus_payload in _generated_phosphorus_payloads():
        direct = PhosphorusOpts()
        direct.parse_inputs(phosphorus_payload)

        prefixed = PhosphorusOpts()
        prefixed.parse_inputs(
            {
                f"phosphorus_opts_{key}": value
                for key, value in phosphorus_payload.items()
            }
        )

        assert prefixed.contents == direct.contents


def test_validate_phosphorus_txt_accepts_generated_wrapper_payload(tmp_path: Path) -> None:
    payload = _generated_phosphorus_payloads()[0]
    opts = PhosphorusOpts()
    opts.parse_inputs(payload)
    assert opts.isvalid

    target = tmp_path / "phosphorus.txt"
    target.write_text(opts.contents, encoding="utf-8")

    assert validate_phosphorus_txt(str(target))


def test_validate_phosphorus_txt_fails_explicitly_on_dimension_or_type_drift(
    tmp_path: Path,
) -> None:
    missing_line = tmp_path / "missing_line.txt"
    missing_line.write_text(
        "Phosphorus concentration\n"
        "1.0\tSurface runoff concentration (mg/l)\n"
        "2.0\tSubsurface lateral flow concentration (mg/l)\n"
        "3.0\tBaseflow concentration (mg/l)\n",
        encoding="utf-8",
    )

    bad_value = tmp_path / "bad_value.txt"
    bad_value.write_text(
        "Phosphorus concentration\n"
        "1.0\tSurface runoff concentration (mg/l)\n"
        "2.0\tSubsurface lateral flow concentration (mg/l)\n"
        "3.0\tBaseflow concentration (mg/l)\n"
        "oops\tSediment concentration (mg/kg)\n",
        encoding="utf-8",
    )

    assert not validate_phosphorus_txt(str(missing_line))
    assert not validate_phosphorus_txt(str(bad_value))
