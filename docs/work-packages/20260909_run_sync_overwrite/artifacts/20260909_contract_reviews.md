# Independent contract reviews — 2026-09-09 UTC

Review A: sync_contract_a (read-only).
- Medium: sidecar validation must explicitly cover symlinks/directories.
  Resolved: combined payload/sidecar paths require safe ancestors and regular
  files or absence before cleanup.
- Medium: reject ancestor conflicts such as `a` and `a/b` or `a.aria2/b`.
  Resolved: combined-set conflict rejection is normative.
- Clarify validation occurs before payload downloading, after manifest fetch.
  Resolved in wording.
- Post-amendment confirmation: no blocking contract findings remain.

Review B: sync_contract_b (read-only).
- Medium: fixed manifest staging could follow a pre-existing symlink.
  Resolved: safe exclusive staging before writing remote bytes is normative;
  staging/sidecar filesystem regressions are required.
- Minor: legitimate empty manifest and missing final newline unspecified.
  Resolved: transfer no-op for empty manifest; accept final record without newline.
- Reserved staging/control-name conflicts now explicitly documented as an
  intentional compatibility restriction.
- Post-amendment confirmation: no contract-review blockers remain.

Author disposition: all proposed changes remain bounded to worker preparation
and replacement semantics. No production implementation edits in this phase.
