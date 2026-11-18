# Default test workflow tracker

Status: Complete locally; not integrated, 2026-11-18 UTC.

- [x] Inspect command registration and Disturbed matrix collection.
- [x] Promote isolated runner and implement explicit matrix opt-in.
- [x] Validate both command paths and default/opt-in collection without running the native matrix.
- [x] Update durable guidance and retain results.

Authority: operator requested the workflow as default and unnecessary Disturbed
matrix execution excluded. This updates current policy, not historical evidence.

Final evidence: 113 passed / 99 deselected. Disturbed default selection 16, explicit
selection 115; Roads selection 516. No native matrix was run. Producer and
published provenance remain unchanged. See artifacts/validation.md.
