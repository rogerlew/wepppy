"""Compare generated output values and construct deterministic evidence."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .artifacts import _normalize_float_string, _sha256_text
from .lookup_stage import LookupEdit, PropertyArtifact, StageOutputs
from .manifest import LiveE2EManifest


def normalized(row: dict[str, str], keys: Iterable[str]) -> dict[str, str]:
    return {key: _normalize_float_string(row.get(key)) for key in keys}


def matches_patch(row: dict[str, str], patch: dict[str, str], fields: Iterable[str] | None = None) -> bool:
    return all(
        _normalize_float_string(row.get(k)) == _normalize_float_string(v)
        for k, v in patch.items()
        if fields is None or k in fields
    )


def matches_pmet(stage: StageOutputs, patch: dict[str, str]) -> bool:
    if not stage.target_pmet_rows:
        return False
    expected = {
        "kcb": _normalize_float_string(patch["pmet_kcb"]),
        "rawp": _normalize_float_string(patch["pmet_rawp"]),
    }
    return all(normalized(row, expected) == expected for row in stage.target_pmet_rows)


def stage_assertions(
    manifest: LiveE2EManifest,
    base: StageOutputs,
    extended: StageOutputs,
    base_edit: LookupEdit,
    extended_edit: LookupEdit,
    base_rows_after_extended: list[dict[str, str]],
    control_before: PropertyArtifact,
    control_after: PropertyArtifact,
    management_after: PropertyArtifact,
) -> dict[str, bool]:
    sol_fields = manifest.target_sol_fields
    return {
        "base_lookup_row_patched": matches_patch(base_edit.target_row, manifest.base_patch),
        "base_sol_propagation": matches_patch(base.target_soil.fields, manifest.base_patch, sol_fields),
        "base_pmetpara_propagation": matches_pmet(base, manifest.base_patch),
        "scope_non_target_unchanged": normalized(control_before.fields, sol_fields)
        == normalized(control_after.fields, sol_fields),
        "extended_lookup_variant_active": str(extended_edit.after.metadata.get("lookup_variant"))
        == "extended",
        "extended_sol_precedence": matches_patch(
            extended.target_soil.fields, manifest.extended_patch, sol_fields
        ),
        "extended_management_propagation": all(
            management_after.fields.get(k) == _normalize_float_string(v)
            for k, v in manifest.extended_patch.items()
            if k in manifest.target_management_fields
        ),
        "base_vs_extended_precedence_pmetpara": matches_pmet(extended, manifest.extended_patch),
        "base_table_unchanged_after_extended_patch": all(
            _normalize_float_string(base_rows_after_extended[base_edit.index].get(key))
            == _normalize_float_string(value)
            for key, value in manifest.base_patch.items()
        ),
    }


def deterministic_payload(
    manifest: LiveE2EManifest,
    base: StageOutputs,
    extended: StageOutputs,
    base_edit: LookupEdit,
    extended_edit: LookupEdit,
    management: PropertyArtifact,
) -> dict[str, Any]:
    return {
        "base_target_sol": normalized(base.target_soil.fields, manifest.target_sol_fields),
        "extended_target_sol": normalized(extended.target_soil.fields, manifest.target_sol_fields),
        "extended_target_management": management.fields,
        "base_target_row": normalized(base_edit.target_row, sorted(manifest.base_patch)),
        "extended_target_row": normalized(extended_edit.target_row, sorted(manifest.extended_patch)),
        "pmet_base": [normalized(row, ("kcb", "rawp")) for row in base.target_pmet_rows],
        "pmet_extended": [normalized(row, ("kcb", "rawp")) for row in extended.target_pmet_rows],
        "artifact_hashes": {
            "target_sol_after_base": _sha256_text(base.target_soil.text),
            "target_sol_after_extended": _sha256_text(extended.target_soil.text),
            "target_man_after_extended": _sha256_text(management.text),
            "pmet_after_base": _sha256_text(base.pmet),
            "pmet_after_extended": _sha256_text(extended.pmet),
        },
    }
