from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tools.peakflow_phase1_protocol import SCHEMAS
from tools.peakflow_phase1_replay import appmth_domain_flags, packetize, verify_packet


pytestmark = pytest.mark.unit


ROOT = Path(__file__).parents[2]
ARTIFACTS = ROOT / "docs/work-packages/20260808_peakflow_phase1/artifacts"


@pytest.mark.parametrize("name", ["topanga-h106-1980-ksat20.json", "topanga-h106-1980-ksat35.json"])
def test_committed_event_packet_is_valid_and_immutable(name: str) -> None:
    packet = json.loads((ARTIFACTS / "event-packets" / name).read_text())
    jsonschema.validate(packet, SCHEMAS["event-packet"])
    verify_packet(packet)


@pytest.mark.parametrize("name", ["topanga-h106-1980-ksat20.json", "topanga-h106-1980-ksat35.json"])
def test_selected_replay_is_exact_and_replay_semantics_are_distinct(name: str) -> None:
    report = json.loads((ARTIFACTS / "replay-reports" / name).read_text())
    assert report["replay_process"] == "standalone_peak_replay_executable"
    assert report["selected_method_delta_m_s"] == 0.0
    assert not report["legacy_input_replay"]["appmth"]["within_documented_vstar_domain"]
    assert report["harmonized_forcing_diagnostic"]["appmth"]["within_documented_vstar_domain"]


def test_negative_control_manifest_is_valid() -> None:
    manifest = json.loads((ARTIFACTS / "negative-control-mutation.json").read_text())
    jsonschema.validate(manifest, SCHEMAS["mutation-manifest"])
    result = json.loads((ARTIFACTS / "negative-control-result.json").read_text())
    assert result["canonical_outputs_all_byte_equal"]
    assert result["input_diff_sha256"] == manifest["input_diff_sha256"]


@pytest.mark.parametrize(
    ("field", "lower", "upper"),
    [("vstar", 0.08, 1.0), ("tstar", 0.09, 10.0), ("qpstar", 0.07, 8.0)],
)
def test_appmth_documented_domain_boundaries(field: str, lower: float, upper: float) -> None:
    values = {"vstar": 0.5, "tstar": 1.0, "qpstar": 1.0}
    key = f"within_documented_{field}_domain"
    for boundary in (lower, upper):
        values[field] = boundary
        assert appmth_domain_flags(**values)[key]
    values[field] = lower - 1e-12
    assert not appmth_domain_flags(**values)[key]
    values[field] = upper + 1e-12
    assert not appmth_domain_flags(**values)[key]


def test_no_surplus_event_packet_is_complete(tmp_path: Path) -> None:
    trace = tmp_path / "trace.csv"
    trace.write_text(
        "SCALAR,1980,45,2,3,1e-3,1e-3,0,0,300,300,2e-6,2e-6,0,1,1,1.5,10,1,0\n"
        "PRE,1980,45,2,3,1,0,300,2e-6\n"
        "POST,1980,45,2,3,1,0,2e-6\n"
        "POST,1980,45,2,3,2,300,0\n"
        "RESULT,1980,45,2,3,APPMTH,3.63e-8\n"
    )
    packet = packetize(trace, 1980, 45, "build", "event", "run", "106", 2, 3)
    assert packet["scalars"]["surplus_assignment_mode"] == "none"
    assert packet["scalars"]["runoff_pre_reconciliation_m"] == 1e-3
    assert packet["pre_surplus_forcing"] == [
        {"interval_ordinal": 1, "start_s": 0.0, "end_s": 300.0, "rate_m_s": 2e-6}
    ]
    assert packet["production"] == {"selected_solver": "APPMTH", "peak_m_s": 3.63e-8}
