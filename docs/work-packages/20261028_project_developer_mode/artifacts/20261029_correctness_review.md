# Correctness and user-experience review — project developer mode

Reviewer: `/root/contract_correctness`, 2026-10-29 UTC. Scope: implementation after ancestor `44746ff63` and native `4d4c075`; current DM-01/SA-01 and ADR-0088. Verdict: no remaining blocking implementation findings; broad-suite completion remains recorded separately.

## User outcome and states

Dev enables Ron-owned mode; ordinary authorized callers can use elevated anisotropy. There is no off toggle. Clones inherit source mode; archive restore and failed-fork recovery replace destination mode with incoming true/false/missing state. No mode-based recovery rejection or sticky state was added.

Missing legacy mode reads false without writing; malformed mode fails before mutation. Blank/omitted overrides preserve existing semantics. Populated normal projects retain 100/10 limits; developer projects retain finite >=1 validation. MOFE/hourly and readonly controls remain authoritative. Existing output remains historical until re-execution; fresh worker output is separately retained.

## Implementation findings

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| R1 | Medium | Elevated runtime/test tuples bypassed the changed preparation facade. | Parameterized actual facade-to-writer test for developer 101/11, normal values and inactive hourly; reviewer confirmed closure. |
| R2 | Medium | Capture concurrency and failed-fork replacement evidence was incomplete. | Actual archive member-copy barrier with Ron/Wepp activation, real restore, failed-fork endpoint rename/delete plus production rsync and decoded incoming state; separate completed real fork worker. Reviewer confirmed closure. |

## Direct evidence and user errors

`test_missing_false_and_enable_refreshes_unrelated_durable_state` proves real fresh-state locking retains concurrent unrelated updates. `test_malformed_persisted_mode_does_not_activate` proves bounded errors and unchanged bytes. Real authorization/CSRF tests cover valid and denied states; expected denied requests do not mutate. Existing validation errors remain for ineligible/invalid inputs; native mismatch fails explicitly. JS tests prove immediate maximum removal without discarding values, and failed activation tells users to reload before retrying.

The actual archive interleaving captures a consistent normal Ron/Wepp pair while activation waits, then restoration correctly restores that pair. Failed-fork tests use real replacement/copy with queue admission stubbed; `runtime.json` independently proves ordinary fork worker copying and rehydration.

## Generated artifact chain

`runtime.json` traces activation through Ron/Wepp persistence, default RQ preparation, rebuilt Rust, generated p1.sol, a successful fresh WEPP hillslope execution and a completed fork. Ratios are 101/101/11 in both OFEs, source hash is unchanged, and output ownership is UID 1000/GID 993/mode 0644. `browser.json` records the actual project page, absent maxima, mode indicator, no activation control for an ordinary viewer, and matching soil/loss-report download hashes. `prepared-p1.sol`, `fresh-H1.loss.dat` and `model-execution.log` retain inspectable evidence.

Highest claim: locally/environment validated bounded preparation and one fresh hillslope simulation on an isolated MOFE project, not broad scientific stability or production deployment. Synthetic activation identity avoids account mutation; the browser checks use ordinary project access. Runtime security review is additional, not a substitute for this review.

## Broad-gate follow-up

The independent reviewer confirmed the one-line `developer_mode=False` addition to the SRID test stand-in; no runtime fallback is needed. Real Ron retains missing-false and malformed-state rejection. The reviewer also confirmed `roads-provenance-baseline.json` supports the unrelated pre-existing Roads source-provenance disposition. No new findings.
