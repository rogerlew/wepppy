"""Exercise runbook orchestration and inspect its artifacts without a live service."""

import csv
import io
import json
from pathlib import Path
from unittest.mock import Mock, create_autospec

import pytest

from tests.nodb.mods.disturbed.live_e2e import (
    execute_live_runbook,
    load_manifest,
    runbook,
)
from tests.nodb.mods.disturbed.live_e2e.api_client import (
    JobWaitResult,
    LiveAPIClient,
    LiveApiError,
)
from tests.nodb.mods.disturbed.live_e2e.artifacts import _parse_management_fields


@pytest.fixture
def replay(monkeypatch):
    manifest = load_manifest()
    monkeypatch.setenv("DEV_AGENT_EMAIL", "replay@example.invalid")
    monkeypatch.setenv("DEV_AGENT_PASSWORD", "replay-password")
    monkeypatch.setattr(runbook, "_generate_target_runid", lambda: "replay-fork")
    monkeypatch.setattr(runbook, "_utcnow_iso", lambda: "replay-time")
    client = create_autospec(LiveAPIClient, instance=True)
    monkeypatch.setattr(runbook, "LiveAPIClient", Mock(return_value=client))
    monkeypatch.setattr(runbook, "_solve_cap_token", lambda *a, **kw: ("cap", {"success": True}))
    client.login_and_mint_dev_agent_bearer.return_value = {"token": "minted"}
    client.issue_session_token.side_effect = [{"token": "source"}, {"token": "fork"}]
    client.discover_cap_endpoint.return_value = "/cap"
    client.fork_run.return_value = {"job_id": "fork-job"}
    client.wait_for_job.side_effect = lambda *, job_id, **kw: JobWaitResult(job_id, {"status": "finished"}, 1)
    client.build_soils.side_effect = ["base-soils", "extended-soils"]
    client.prep_wepp_watershed.side_effect = ["base-prep", "extended-prep"]
    client.disturbed_lookup_meta.return_value = {"lookup_sha256": "source-hash"}

    man = (Path(__file__).parents[3] / "wepp_runner/fixtures/hillslope_smoke/runs/p1.man").read_text()
    manifest.raw["patches"]["extended"].update(
        _parse_management_fields(man, management_fields=manifest.target_management_fields)
    )
    fields = manifest.extended_patch
    target = dict.fromkeys(fields, "0") | {"luse": manifest.target_luse, "stext": manifest.target_stext}
    control = target | {"luse": "control"}
    tables = {"base": [target, control]}
    active = "base"

    def snapshot(*, lookup, **kwargs):
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=target.keys())
        writer.writeheader()
        writer.writerows(tables[lookup])
        return {"csv_text": buffer.getvalue(), "lookup_sha256": lookup, "lookup_variant": lookup}

    def modify(*, rows, lookup, expected_statuses, **kwargs):
        if expected_statuses == (200,):
            tables[lookup] = rows
            return Mock(headers={"X-Lookup-Sha256": lookup})
        if expected_statuses == (409,):
            error = {"code": "STALE_LOOKUP"}
        elif len(rows[0]) == 2:
            error = {"message": "missing columns"}
        else:
            error = {"message": "missing existing lookup rows"}
        return Mock(json=lambda: {"error": error})

    def sync(**kwargs):
        nonlocal active
        active = "extended"
        tables[active] = tables["base"]

    def download(*, runid, subpath, **kwargs):
        if runid == manifest.source_runid:
            return "source pmet"
        row = tables[active][0]
        if subpath.endswith("pmetpara.txt"):
            return (
                f"plant,kcb,rawp,index,description\n1,{row['pmet_kcb']},{row['pmet_rawp']},"
                f"1,{manifest.target_pmet_description}\n2,0,0,2,control\n"
            )
        if subpath.endswith(".man"):
            return man
        if subpath.endswith("p2.sol"):
            row = control
        return "# Replacements\n" + "".join(f"# {key} -> {value}\n" for key, value in row.items())

    client.download_text.side_effect = download
    client.disturbed_lookup_snapshot.side_effect = snapshot
    client.disturbed_modify.side_effect = modify
    client.sync_base_to_extended_lookup.side_effect = sync
    return manifest, client


def test_replay_records_stage_outputs(tmp_path, replay):
    manifest, client = replay
    result = execute_live_runbook(manifest=manifest, evidence_root=tmp_path, run_label="replay")
    evidence = json.loads(result.evidence_json_path.read_text())
    assert len(result.assertions) == 19
    assert all(result.assertions.values()), result.assertions
    assert evidence["phase"] == "completed"
    assert evidence["determinism"]["signature"] == result.deterministic_signature
    assert (
        evidence["lookup_rows"]["base_after_patch"]["target_row"]["pmet_kcb"]
        == manifest.base_patch["pmet_kcb"]
    )
    assert (
        evidence["artifact_hashes"]["control_sol_before"]
        == evidence["artifact_hashes"]["control_sol_after_base"]
    )
    assert "PASS: `extended_management_propagation`" in result.evidence_markdown_path.read_text()
    assert [call.kwargs["job_id"] for call in client.wait_for_job.call_args_list] == [
        "fork-job",
        "base-soils",
        "base-prep",
        "extended-soils",
        "extended-prep",
    ]


def test_replay_records_failed_stage(tmp_path, replay):
    manifest, client = replay
    client.prep_wepp_watershed.side_effect = LiveApiError("prep unavailable")
    with pytest.raises(LiveApiError, match="prep unavailable"):
        execute_live_runbook(manifest=manifest, evidence_root=tmp_path, run_label="replay")
    (evidence_path,) = tmp_path.glob("*/evidence.json")
    evidence = json.loads(evidence_path.read_text())
    assert evidence["failure"] == {
        "type": "LiveApiError",
        "message": "prep unavailable",
        "phase": "running_base_prep_wepp",
    }
    assert evidence["all_assertions_passed"] is False
    assert "prep unavailable" in evidence_path.with_suffix(".md").read_text()


def test_replay_reports_unpropagated_soil_value(tmp_path, replay):
    manifest, client = replay
    download = client.download_text.side_effect

    def corrupt_soil(**kwargs):
        text = download(**kwargs)
        if kwargs["subpath"].endswith("p1.sol"):
            return text.replace("# rdmax -> " + manifest.base_patch["rdmax"], "# rdmax -> 0")
        return text

    client.download_text.side_effect = corrupt_soil
    result = execute_live_runbook(manifest=manifest, evidence_root=tmp_path, run_label="replay")
    assert [name for name, passed in result.assertions.items() if not passed] == ["base_sol_propagation"]
    evidence = json.loads(result.evidence_json_path.read_text())
    assert evidence["phase"] == "completed"
    assert evidence["all_assertions_passed"] is False
    assert "FAIL: `base_sol_propagation`" in result.evidence_markdown_path.read_text()


def test_replay_reports_truncated_patch_response_at_patch_phase(tmp_path, replay):
    manifest, client = replay
    snapshot = client.disturbed_lookup_snapshot.side_effect
    responses = 0

    def truncate(**kwargs):
        nonlocal responses
        responses += 1
        response = snapshot(**kwargs)
        if responses == 2:
            response["csv_text"] = ""
        return response

    client.disturbed_lookup_snapshot.side_effect = truncate
    with pytest.raises(IndexError):
        execute_live_runbook(manifest=manifest, evidence_root=tmp_path, run_label="replay")
    (evidence_path,) = tmp_path.glob("*/evidence.json")
    assert json.loads(evidence_path.read_text())["failure"]["phase"] == "patching_base_lookup"
    client.build_soils.assert_not_called()
