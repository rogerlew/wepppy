from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from tools.rq_engine_contract_rules import required_response_codes

pytestmark = pytest.mark.microservice


INVENTORY_FILE = Path(
    "docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md"
)

MAX_OPENAPI_CANONICAL_BYTES = 90_000
MAX_FROZEN_SUMMARY_CHARS = 72
MAX_FROZEN_DESCRIPTION_CHARS = 280
MAX_FROZEN_METADATA_TOTAL_CHARS = 12_000
_CORRELATION_HEADER = "X-Correlation-ID"
_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _strip_markdown_code(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1]
    return stripped


def _load_frozen_agent_routes(repo_root: Path) -> list[tuple[str, str]]:
    lines = (repo_root / INVENTORY_FILE).read_text(encoding="utf-8").splitlines()

    in_table = False
    routes: list[tuple[str, str]] = []
    for line in lines:
        if line.strip().startswith("| Method | Path | Module | Function | Classification | Owner |"):
            in_table = True
            continue
        if not in_table:
            continue

        stripped = line.strip()
        if not stripped.startswith("|"):
            if routes:
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
            routes.append((method, path))

    return routes


@pytest.fixture(scope="module")
def _openapi_doc() -> dict:
    with TestClient(rq_engine.app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="module")
def _frozen_agent_routes() -> list[tuple[str, str]]:
    repo_root = Path(__file__).resolve().parents[2]
    return _load_frozen_agent_routes(repo_root)


def _response_codes(operation: dict) -> set[int]:
    codes: set[int] = set()
    for key in operation.get("responses", {}):
        try:
            codes.add(int(key))
        except (TypeError, ValueError):
            continue
    return codes


def _canonical_size_bytes(payload: dict) -> int:
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return len(serialized)


def test_frozen_agent_route_count_is_expected(_frozen_agent_routes: list[tuple[str, str]]) -> None:
    assert len(_frozen_agent_routes) == 54
    assert len(set(_frozen_agent_routes)) == 54


def test_frozen_agent_routes_exist_in_openapi(
    _openapi_doc: dict,
    _frozen_agent_routes: list[tuple[str, str]],
) -> None:
    paths = _openapi_doc["paths"]
    missing: list[str] = []
    for method, path in _frozen_agent_routes:
        method_key = method.lower()
        operation = paths.get(path, {}).get(method_key)
        if operation is None:
            missing.append(f"{method} {path}")
    assert missing == []


def test_frozen_agent_route_metadata_fields_are_non_empty(
    _openapi_doc: dict,
    _frozen_agent_routes: list[tuple[str, str]],
) -> None:
    paths = _openapi_doc["paths"]
    for method, path in _frozen_agent_routes:
        operation = paths[path][method.lower()]
        summary = str(operation.get("summary", "")).strip()
        description = str(operation.get("description", "")).strip()
        tags = operation.get("tags", [])
        operation_id = str(operation.get("operationId", "")).strip()

        assert summary
        assert description
        assert isinstance(tags, list) and len(tags) > 0
        assert operation_id
        assert operation_id.startswith("rq_engine_")
        assert len(tags) <= 2

        description_lower = description.lower()
        assert any(
            token in description_lower
            for token in (
                "requires jwt",
                "supports",
                "open by default",
                "bearer",
            )
        )
        assert any(
            token in description_lower
            for token in (
                "enqueue",
                "synchronously",
                "read-only",
                "no queue",
                "redirect",
            )
        )


def test_frozen_agent_operation_ids_are_unique(
    _openapi_doc: dict,
    _frozen_agent_routes: list[tuple[str, str]],
) -> None:
    paths = _openapi_doc["paths"]
    operation_ids: list[str] = []
    for method, path in _frozen_agent_routes:
        operation = paths[path][method.lower()]
        operation_ids.append(operation["operationId"])

    assert len(operation_ids) == len(set(operation_ids))


def test_frozen_agent_required_response_codes_documented(
    _openapi_doc: dict,
    _frozen_agent_routes: list[tuple[str, str]],
) -> None:
    paths = _openapi_doc["paths"]
    for method, path in _frozen_agent_routes:
        operation = paths[path][method.lower()]
        codes = _response_codes(operation)
        expected_codes = required_response_codes(method, path)
        assert expected_codes.issubset(codes), (
            f"{method} {path} missing response codes. "
            f"required={sorted(expected_codes)} documented={sorted(codes)}"
        )

        for auth_code in (401, 403, 500):
            description = str(operation["responses"][str(auth_code)]["description"]).lower()
            assert "canonical error payload" in description


def test_openapi_document_size_budget(_openapi_doc: dict) -> None:
    size_bytes = _canonical_size_bytes(_openapi_doc)
    assert size_bytes <= MAX_OPENAPI_CANONICAL_BYTES, (
        "OpenAPI document exceeded size budget. "
        f"size_bytes={size_bytes} budget_bytes={MAX_OPENAPI_CANONICAL_BYTES}"
    )


def test_openapi_response_emits_correlation_header() -> None:
    with TestClient(rq_engine.app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    correlation_id = response.headers.get(_CORRELATION_HEADER)
    assert correlation_id is not None
    assert _CORRELATION_ID_PATTERN.match(correlation_id)


def test_openapi_response_replaces_invalid_correlation_header() -> None:
    with TestClient(rq_engine.app) as client:
        response = client.get(
            "/openapi.json",
            headers={_CORRELATION_HEADER: "invalid id with spaces"},
        )

    assert response.status_code == 200
    correlation_id = response.headers.get(_CORRELATION_HEADER)
    assert correlation_id is not None
    assert correlation_id != "invalid id with spaces"
    assert _CORRELATION_ID_PATTERN.match(correlation_id)


def test_frozen_agent_metadata_size_budgets(
    _openapi_doc: dict,
    _frozen_agent_routes: list[tuple[str, str]],
) -> None:
    paths = _openapi_doc["paths"]
    total_chars = 0

    for method, path in _frozen_agent_routes:
        operation = paths[path][method.lower()]
        summary = str(operation.get("summary", "")).strip()
        description = str(operation.get("description", "")).strip()
        total_chars += len(summary) + len(description)

        assert len(summary) <= MAX_FROZEN_SUMMARY_CHARS, (
            f"{method} {path} summary too long. "
            f"len={len(summary)} budget={MAX_FROZEN_SUMMARY_CHARS}"
        )
        assert len(description) <= MAX_FROZEN_DESCRIPTION_CHARS, (
            f"{method} {path} description too long. "
            f"len={len(description)} budget={MAX_FROZEN_DESCRIPTION_CHARS}"
        )

    assert total_chars <= MAX_FROZEN_METADATA_TOTAL_CHARS, (
        "Frozen agent-route OpenAPI metadata exceeded aggregate budget. "
        f"total_chars={total_chars} budget={MAX_FROZEN_METADATA_TOTAL_CHARS}"
    )
