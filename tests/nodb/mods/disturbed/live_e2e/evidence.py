"""Persist checkpoints for the live runbook."""

import json
from pathlib import Path
from typing import Any


def _write_evidence_artifacts(
    *,
    evidence_dir: Path,
    evidence: dict[str, Any],
) -> tuple[Path, Path]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_json_path = evidence_dir / "evidence.json"
    evidence_markdown_path = evidence_dir / "evidence.md"

    evidence_json_path.write_text(json.dumps(evidence, indent=2, sort_keys=True))

    cleanup = evidence.get("cleanup") or {}
    resource_scope = evidence.get("resource_scope") or {}
    target_scope = resource_scope.get("target") or {}
    control_scope = resource_scope.get("control") or {}
    assertions = evidence.get("assertions") or {}

    summary_lines = [
        "# Disturbed Lookup Live E2E Evidence",
        "",
        f"- run_label: `{evidence.get('run_label', '')}`",
        f"- phase: `{evidence.get('phase', 'unknown')}`",
        f"- fork_runid: `{(evidence.get('fork') or {}).get('fork_runid', 'pending')}`",
        f"- all_assertions_passed: `{evidence.get('all_assertions_passed', False)}`",
        f"- deterministic_signature: `{(evidence.get('determinism') or {}).get('signature', 'pending')}`",
        f"- cleanup_status: `{cleanup.get('status', 'unknown')}`",
        "",
        "## Assertions",
        "",
    ]
    for name, passed in sorted(assertions.items()):
        summary_lines.append(f"- {'PASS' if passed else 'FAIL'}: `{name}`")

    failure = evidence.get("failure")
    if failure:
        summary_lines.extend(
            [
                "",
                "## Failure",
                "",
                f"- type: `{failure.get('type', 'unknown')}`",
                f"- phase: `{failure.get('phase', 'unknown')}`",
                f"- message: `{failure.get('message', '')}`",
            ]
        )

    summary_lines.extend(
        [
            "",
            "## Key Artifacts",
            "",
            f"- target_sol: `{target_scope.get('sol_subpath', 'pending')}`",
            f"- target_man: `{target_scope.get('man_subpath', 'pending')}`",
            f"- control_sol: `{control_scope.get('sol_subpath', 'pending')}`",
            f"- pmet_description: `{(evidence.get('pmetpara') or {}).get('target_description', 'pending')}`",
            "",
            "## Endpoint Trace",
            "",
            f"- total_calls: `{len(evidence.get('endpoint_calls') or [])}`",
        ]
    )
    evidence_markdown_path.write_text("\n".join(summary_lines) + "\n")

    return evidence_json_path, evidence_markdown_path
