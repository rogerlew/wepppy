# Contract Review Disposition - CLIMATE-SEED-01

## Summary

Both independent read-only reviews blocked the initial draft. The corrected
proposal separates explicit configuration from generated runtime state and
preserves current effective defaults. Both reviewers confirmed the corrected
proposal, and the operator approved the exact matrix at 2026-10-05 19:43 UTC.

## Disposition

| Finding | Severity | Resolution | Status |
| --- | --- | --- | --- |
| Generated/runtime seed would change defaults | High | Persist user intent in additive `_cligen_seed_override`; leave `_cligen_seed` runtime-only; `None` retains omitted argv or modified-path `-r12345` exactly | Resolved; both reviewers confirmed |
| Exact matrix not operator-approved | High | Present corrected matrix for explicit approval before checkpoint | Resolved; approved 2026-10-05 19:43 UTC |
| Batch explicit/generated ambiguity | High | Copy only `_cligen_seed_override` base-to-leaf; continue excluding `_cligen_seed` | Resolved; both reviewers confirmed |
| `canine-liar` recovery incomplete | High | Validate on a normalized disposable `fork_rq` destination and require source-project manifest equivalence | Resolved after execution re-review |
| Tenerife mismatch | Medium | Render the seed advanced control for Tenerife while retaining other exclusions | Resolved in proposal |
| Malformed durable/read-only states | Medium | Fail malformed durable override before execution; add read-only render/submission tests | Resolved in proposal |
| Omission wording | Medium | Distinguish absent-preserve from empty-clear throughout package | Resolved in proposal |
| Single-storm unsupported | Medium | Cover dormant helper forwarding only; do not enable or claim mode support | Resolved in proposal |
| End-to-end fidelity vague | Medium | Require route -> persisted reload -> job metadata replay -> `Climate.build` -> real binary -> parsed output on normalized fork | Resolved in proposal |
| Multiple-worker semantics broad | Medium | Snapshot observed collect/finalize paths; capture once under lock for modified worker pools | Resolved in proposal |
| Native seed semantics | Medium | Document stream advancement, zero and prohibited `-1`; test `0`, representative positive, `99999` | Resolved in proposal |
| Integer lexical form | Low | Trim whitespace, accept digits/leading zeros, reject signs | Resolved in proposal |

## Corrected approval matrix

| Dimension | Proposed rule |
| --- | --- |
| Persistence | `cligen_seed` writes `_cligen_seed_override: int | None`; existing `_cligen_seed` remains runtime-only |
| Omitted request | Preserve current override |
| Empty/null request | Clear override to `None` |
| Accepted values | JSON integer or trimmed digit string `0..99999`; leading zeros accepted |
| Rejected values | bool, float, fractional/text/signed string, negative, `>99999`, including native clock seed `-1` |
| Automatic behavior | Vanilla/observed omit `-r`; modified PRISM/E-OBS/AGDC retain effective `-r12345` |
| Explicit behavior | Every applicable active CLIGEN path gets exactly one `-rN` |
| Batch | Copy override base-to-leaf; do not copy generated runtime seed |
| Tenerife | Seed field visible; unrelated advanced fields retain existing rules |
| Single storm | Forward through dormant helper interface only; do not enable unsupported modes |
| Malformed durable override | Fail build before CLIGEN; never silently downgrade |
| Project evidence | Complete normalized `canine-liar` fork through `fork_rq(..., skip_omni_scenarios_contrasts=True)`; source project exact before/after manifest |

## Gate

The matrix is approved and both independent reviewers confirmed the corrected
contract. The standalone checkpoint commit is the only remaining gate.
