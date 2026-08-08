from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tools.peakflow_phase1_protocol import SCHEMAS
from tools.peakflow_phase1_replay import verify_packet


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
