from __future__ import annotations

import os
from pathlib import Path

import pytest
from _pytest.config import Config

from tests.nodb.mods.disturbed.live_e2e import execute_live_runbook, load_manifest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_network,
    pytest.mark.slow,
    pytest.mark.nodb,
]

_RUN_FLAG = "DISTURBED_LOOKUP_LIVE_E2E"
_TRUE_VALUES = {"1", "true", "yes", "on"}


def _require_live_enabled(pytestconfig: Config) -> None:
    if os.getenv("PYTEST_CURRENT_TEST") is None:
        return
    if bool(pytestconfig.getoption("--live-disturbed-lookup-e2e")):
        return
    if os.getenv(_RUN_FLAG, "").strip().lower() not in _TRUE_VALUES:
        pytest.skip(
            f"Set {_RUN_FLAG}=1 or pass --live-disturbed-lookup-e2e to run disturbed lookup live E2E tests."
        )


def _assertions_text(assertions: dict[str, bool]) -> str:
    return ", ".join(
        f"{name}={'PASS' if passed else 'FAIL'}"
        for name, passed in sorted(assertions.items())
    )


@pytest.mark.integration
def test_disturbed_lookup_live_runbook_deterministic(pytestconfig: Config) -> None:
    _require_live_enabled(pytestconfig)

    manifest = load_manifest()
    evidence_root = Path(
        os.getenv(
            "DISTURBED_LOOKUP_LIVE_E2E_EVIDENCE_DIR",
            "/tmp/wepppy-disturbed-lookup-live-e2e",
        )
    )
    evidence_root.mkdir(parents=True, exist_ok=True)

    result_a = execute_live_runbook(
        manifest=manifest,
        evidence_root=evidence_root,
        run_label="determinism_a",
    )
    assert all(result_a.assertions.values()), _assertions_text(result_a.assertions)

    result_b = execute_live_runbook(
        manifest=manifest,
        evidence_root=evidence_root,
        run_label="determinism_b",
    )
    assert all(result_b.assertions.values()), _assertions_text(result_b.assertions)

    assert result_a.deterministic_signature == result_b.deterministic_signature

    print(f"run_a evidence: {result_a.evidence_json_path}")
    print(f"run_b evidence: {result_b.evidence_json_path}")
    print(f"deterministic_signature: {result_a.deterministic_signature}")
