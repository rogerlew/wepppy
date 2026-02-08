#!/usr/bin/env python3
"""Validate route-contract checklist parity and required fields."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

INVENTORY_FILE = Path(
    "docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md"
)
CHECKLIST_FILE = Path(
    "docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md"
)

_ALLOWED_MUTATES = {"mutating", "read-only"}
_ALLOWED_EXECUTION = {"async enqueue", "sync", "sync no queue", "sync redirect"}


@dataclass(frozen=True)
class ChecklistRecord:
    method: str
    path: str
    auth: str
    scope: str
    mutates: str
    execution: str
    required_responses: str
    contract_coverage: str


def _strip_markdown_code(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("`") and stripped.endswith("`") and len(stripped) >= 2:
        return stripped[1:-1]
    return stripped


def _parse_inventory_keys(repo_root: Path) -> set[tuple[str, str]]:
    inventory_path = repo_root / INVENTORY_FILE
    lines = inventory_path.read_text(encoding="utf-8").splitlines()

    in_table = False
    keys: set[tuple[str, str]] = set()
    for line in lines:
        if line.strip().startswith("| Method | Path | Module | Function | Classification | Owner |"):
            in_table = True
            continue

        if not in_table:
            continue

        stripped = line.strip()
        if not stripped.startswith("|"):
            if keys:
                break
            continue
        if stripped.startswith("|---"):
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 6:
            continue

        method, path, _module, _function, classification, owner = cells[:6]
        method = _strip_markdown_code(method).upper()
        path = _strip_markdown_code(path)
        classification = _strip_markdown_code(classification)
        owner = _strip_markdown_code(owner)
        if classification == "agent-facing" and owner == "rq-engine":
            keys.add((method, path))

    return keys


def _parse_checklist(repo_root: Path) -> dict[tuple[str, str], ChecklistRecord]:
    checklist_path = repo_root / CHECKLIST_FILE
    lines = checklist_path.read_text(encoding="utf-8").splitlines()

    in_table = False
    records: dict[tuple[str, str], ChecklistRecord] = {}
    for line in lines:
        if line.strip().startswith(
            "| Method | Path | Auth | Scope | Mutates | Execution | Required Responses | Contract Coverage |"
        ):
            in_table = True
            continue

        if not in_table:
            continue

        stripped = line.strip()
        if not stripped.startswith("|"):
            if records:
                break
            continue
        if stripped.startswith("|---"):
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 8:
            continue

        method, path, auth, scope, mutates, execution, required_responses, contract_coverage = cells[:8]
        method = _strip_markdown_code(method).upper()
        path = _strip_markdown_code(path)
        key = (method, path)
        records[key] = ChecklistRecord(
            method=method,
            path=path,
            auth=_strip_markdown_code(auth),
            scope=_strip_markdown_code(scope),
            mutates=_strip_markdown_code(mutates),
            execution=_strip_markdown_code(execution),
            required_responses=_strip_markdown_code(required_responses),
            contract_coverage=_strip_markdown_code(contract_coverage),
        )

    return records


def _parse_response_codes(value: str) -> set[int]:
    codes: set[int] = set()
    for token in re.split(r"\s*,\s*", value.strip()):
        if not token:
            continue
        try:
            codes.add(int(token))
        except ValueError:
            continue
    return codes


def collect_checklist_issues(repo_root: Path | None = None) -> list[str]:
    root = repo_root or Path(__file__).resolve().parents[1]
    inventory_keys = _parse_inventory_keys(root)
    checklist = _parse_checklist(root)
    checklist_keys = set(checklist)

    issues: list[str] = []

    for method, path in sorted(inventory_keys - checklist_keys):
        issues.append(f"Checklist missing route: {method} {path}")
    for method, path in sorted(checklist_keys - inventory_keys):
        issues.append(f"Checklist contains non-frozen route: {method} {path}")

    for key in sorted(inventory_keys & checklist_keys):
        record = checklist[key]
        route_label = f"{record.method} {record.path}"

        if not record.auth:
            issues.append(f"Checklist auth missing: {route_label}")
        if not record.scope:
            issues.append(f"Checklist scope missing: {route_label}")
        if record.mutates not in _ALLOWED_MUTATES:
            issues.append(
                f"Checklist mutates value invalid for {route_label}: {record.mutates!r} "
                f"(allowed: {sorted(_ALLOWED_MUTATES)})"
            )
        if record.execution not in _ALLOWED_EXECUTION:
            issues.append(
                f"Checklist execution value invalid for {route_label}: {record.execution!r} "
                f"(allowed: {sorted(_ALLOWED_EXECUTION)})"
            )
        if not record.required_responses:
            issues.append(f"Checklist required responses missing: {route_label}")
        if not record.contract_coverage:
            issues.append(f"Checklist contract coverage missing: {route_label}")

        codes = _parse_response_codes(record.required_responses)
        for required_code in (401, 403, 500):
            if required_code not in codes:
                issues.append(
                    f"Checklist required responses missing {required_code}: {route_label} "
                    f"({record.required_responses})"
                )

        has_success = any(200 <= code < 400 for code in codes)
        if not has_success:
            issues.append(
                f"Checklist required responses missing success code: {route_label} "
                f"({record.required_responses})"
            )

        if "test_rq_engine_openapi_contract.py" not in record.contract_coverage:
            issues.append(
                "Checklist contract coverage must include "
                f"tests/microservices/test_rq_engine_openapi_contract.py for {route_label}"
            )

    return issues


def main() -> int:
    issues = collect_checklist_issues()
    if not issues:
        print("Route contract checklist check passed")
        return 0

    print("Route contract checklist drift detected:")
    for issue in issues:
        print(f"- {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
