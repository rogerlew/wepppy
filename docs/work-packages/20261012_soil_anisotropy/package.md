# MOFE soil anisotropy advanced options

Status: implemented on forest; final acceptance in progress. Owner: requesting operator; implementer: Codex.

Add optional upper (1–100) and lower (1–10) horizon anisotropy overrides in WEPP Advanced Options / Soil Options. Editing requires MOFE plus hourly water balance/deep seepage (`run_wepp_ui`). Warn that values above 10 can cause numerical instabilities. Preserve existing soil values when unset. Native Rust owns the new depth classification and value validation, using the already parsed in-memory soil without another file pass.

Complexity budget: no new dependency, service, queue, privilege, or deployment topology. Reuse the existing wepppyo3 interchange extension and Python soil parser/writer. Address confirmed duplicate reads in symbolic and uploaded-native preparation; retain formulas, serialization, and operation ordering. Scope includes rebuilding the affected native release artifact for forest validation, not production deployment or automatic push.

Security impact: low; bounded numeric inputs through existing run authorization/CSRF and NoDb locking. Required independent contract reviews and final correctness review apply. No auth policy changes. Canonical behavior: [soil anisotropy contract](../../schemas/soil-anisotropy-contract.md); parameter decision: ADR-0088. See [active plan](prompts/active/soil_anisotropy_execplan.md).
