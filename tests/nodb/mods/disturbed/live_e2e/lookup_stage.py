"""Read, modify, and rebuild the two lookup variants on the fork."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .api_client import LiveAPIClient
from .artifacts import (
    _apply_patch,
    _artifact_text_hash,
    _canonical_hash,
    _find_lookup_row_index,
    _parse_lookup_rows,
    _parse_management_fields,
    _parse_pmetpara,
    _parse_sol_replacements,
)
from .manifest import LiveE2EManifest


@dataclass
class LookupSnapshot:
    metadata: dict[str, Any]
    rows: list[dict[str, str]]

    def row_evidence(self, index: int) -> dict[str, Any]:
        row = self.rows[index]
        return {
            "lookup_sha256": self.metadata.get("lookup_sha256"),
            "row_count": len(self.rows),
            "target_row": dict(row),
            "target_row_sha256": _canonical_hash(row),
        }


@dataclass
class LookupEdit:
    after: LookupSnapshot
    index: int
    response_sha: str | None
    target_row: dict[str, str]

    def after_evidence(self) -> dict[str, Any]:
        return self.after.row_evidence(self.index) | {"response_lookup_sha256": self.response_sha}


@dataclass
class PropertyArtifact:
    text: str
    fields: dict[str, str]
    path: str

    def fingerprint(self) -> dict[str, Any]:
        return _artifact_text_hash(subpath=self.path, text=self.text)


@dataclass
class StageOutputs:
    jobs: dict[str, Any]
    pmet: str
    target_pmet_rows: list[dict[str, str]]
    target_soil: PropertyArtifact


@dataclass
class ForkLookup:
    client: LiveAPIClient
    manifest: LiveE2EManifest
    scope: dict[str, str]

    def snapshot(self, variant: str) -> LookupSnapshot:
        meta = self.client.disturbed_lookup_snapshot(**self.scope, lookup=variant)
        return LookupSnapshot(meta, _parse_lookup_rows(str(meta.get("csv_text") or "")))

    def target_index(self, snapshot: LookupSnapshot) -> int:
        return _find_lookup_row_index(
            snapshot.rows, luse=self.manifest.target_luse, stext=self.manifest.target_stext
        )

    def patch(self, variant: str, before: LookupSnapshot, index: int, patch: dict[str, str]) -> LookupEdit:
        response = self.client.disturbed_modify(
            **self.scope,
            lookup=variant,
            rows=_apply_patch(before.rows, row_index=index, patch=patch),
            if_match_sha256=str(before.metadata.get("lookup_sha256") or ""),
            expected_statuses=(200,),
        )
        after = self.snapshot(variant)
        target_row = dict(after.rows[index])
        return LookupEdit(after, index, response.headers.get("X-Lookup-Sha256"), target_row)

    def negative_cases(self, before: LookupSnapshot) -> dict[str, Any]:
        def reject(rows: list[dict[str, str]], sha: str, status: int) -> dict[str, Any]:
            return self.client.disturbed_modify(
                **self.scope,
                lookup="base",
                rows=rows,
                if_match_sha256=sha,
                expected_statuses=(status,),
            ).json()

        current_sha = str(before.metadata.get("lookup_sha256") or "")
        return {
            "stale": reject(before.rows, self.manifest.stale_sha256, 409),
            "partial_rows": reject(before.rows[:1], current_sha, 400),
            "invalid_columns": reject(
                [{"luse": self.manifest.target_luse, "stext": self.manifest.target_stext}], current_sha, 400
            ),
        }

    def soil(self, resource: dict[str, Any]) -> PropertyArtifact:
        path = str(resource["sol_subpath"])
        text = self.client.download_text(**self.scope, subpath=path)
        return PropertyArtifact(text, _parse_sol_replacements(text), path)

    def management(self, resource: dict[str, Any]) -> PropertyArtifact:
        path = str(resource["man_subpath"])
        text = self.client.download_text(**self.scope, subpath=path)
        fields = _parse_management_fields(text, management_fields=self.manifest.target_management_fields)
        return PropertyArtifact(text, fields, path)

    def wait(self, job_id: str, timeout: int) -> dict[str, Any]:
        result = self.client.wait_for_job(
            job_id=job_id,
            timeout_seconds=timeout,
            poll_interval_seconds=self.manifest.poll_interval_seconds,
            bearer_token=self.scope["bearer_token"],
        )
        return {"job_id": job_id, "wait_seconds": result.elapsed_seconds, "status": result.status_payload}

    def rebuild(self, variant: str, target: dict[str, Any], evidence: dict[str, Any]) -> StageOutputs:
        evidence["phase"] = f"running_{variant}_build_soils"
        soils = self.wait(self.client.build_soils(**self.scope), self.manifest.build_soils_timeout_seconds)
        evidence["phase"] = f"running_{variant}_prep_wepp"
        prep = self.wait(
            self.client.prep_wepp_watershed(**self.scope), self.manifest.prep_wepp_timeout_seconds
        )
        evidence["phase"] = f"capturing_{variant}_outputs"
        pmet = self.client.download_text(**self.scope, subpath="wepp/runs/pmetpara.txt")
        rows = [
            row
            for row in _parse_pmetpara(pmet)
            if row.get("description") == self.manifest.target_pmet_description
        ]
        return StageOutputs({"build_soils": soils, "prep_wepp": prep}, pmet, rows, self.soil(target))
