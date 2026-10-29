# DM-01 contract decision checkpoint

Prepared: 2026-10-29 00:51 UTC. Base implementation: `cebb4b4283e408fd270126811f4dbbd1a8dfd8e2`.
Status: operator-approved core behavior; two independent reviews complete, lifecycle replacement policy approved and independently confirmed; all design findings closed; no ancestor commit or implementation yet.

## Approval and exact delta

The operator approved Ron-owned project mode, a PowerUser-panel activation restricted to the developer role, permanent activation, project-mode-only anisotropy maximum enforcement, no submission-time Dev-role check and clone inheritance. Their final instruction authorized authoring the contract, scaffolding implementation and dispatching reviewers. This authorizes no runtime changes in this session.

DM-01 introduces missing-false boolean state and one-way activation. SA-01 changes only override maxima: normal remains upper 100/lower 10; developer has neither maximum while finite >=1 checks remain. Both roles and project access are checked at activation; thereafter ordinary operation authorization is unchanged. Exact existing role spelling is `Dev`, not a new role. No unrelated owner is advanced or closed.

Operator clarification, 2026-10-29 01:06 UTC: preserve existing archive restore and failed-fork recovery semantics. Incoming archived/source mode is authoritative even when it replaces activated mode with false or legacy-missing state. Do not add downgrade denial, destination-state preservation or a new Dev check. This explicit exception limits permanence to ordinary mode editing and prioritizes usable recovery and implementation simplicity.

## Applicable authority and classification

| Authority | Disposition |
| --- | --- |
| `docs/schemas/project-developer-mode-contract.md` | New canonical lifecycle, activation and clone policy; pending implementation |
| `docs/schemas/soil-anisotropy-contract.md` | Amend bounds and policy propagation; all other obligations retained |
| `docs/adrs/ADR-0088-soil-anisotropy-overrides.md` | Add approved threshold exception and rationale |
| `docs/schemas/nodb-persistence-concurrency-contract.md` | Unchanged lock/refresh/atomic persistence requirements |
| `docs/schemas/weppcloud-csrf-contract.md` | Unchanged session mutation protections |
| `docs/schemas/rq-response-contract.md` | Unchanged async error/validation response behavior |
| `docs/ui-docs/controller-contract.md` | Unchanged shared UI, tests-first and readonly behavior |
| `docs/schemas/feature-access-governance-contract.md` | Ordinary project authorization unchanged; cross-link project-policy distinction |
| `wepppy/weppcloud/feature_registry/specification.md` | No new registry feature/group or min-role hierarchy; cross-link distinction |
| `docs/schemas/project-owned-config-contract.md` | Mode is Ron state, not project config; no normative change |
| `docs/schemas/project-creation-policy.md` | New projects default normal; clone policy in DM-01; ordinary creation authorization unchanged |

Classification: intended enhancement, not repair of a defect. Current hard-coded UI/Python/Rust bounds conform to the prior contract. The new contract is not evidence that deployment occurred.

Activation transport: `POST /runs/<runid>/<config>/tasks/enable_developer_mode`, JSON `{}`, existing session CSRF header; HTTP 200 `{"Content":{"developer_mode":true}}` using `success_factory`. DM-01 defines malformed-payload 400 and authorization/readonly 403 behavior; no disable field is accepted. This follows adjacent project metadata routes without adding RQ work.

## Source boundary and regression evidence

Candidate paths: `wepppy/nodb/core/ron.py` and `.pyi`; `wepppy/nodb/core/soil_anisotropy.py`; Wepp input/preparation collaborators and stubs; `wepppy/wepp/soils/utils/wepp_soil_util.py` and `.pyi`; PowerUser template, panel entry point and paired JS; `wepppy/weppcloud/routes/nodb_api/project_bp.py`; existing fork/archive consumers only where needed to preserve state; native `wepp_interchange/src/soil_anisotropy.rs` in sibling wepppyo3. Tests and affected documentation are included. No queue edge change is planned.

Compatibility: additive missing-false state; no bulk migration, key removal or normal-project behavior change. Clone/restore regression plan precedes data changes. Security: high, exact Dev-only activation plus ordinary scope/readonly/CSRF; neither mode spoofing nor wider panel access can enable unrelated actions. Regression evidence must include real locked persistence, both authorized and denied HTTP requests, Dev-only UI, authorized non-Dev elevated submission, real native output, clone/archive readback and full workflow under production-equivalent identity.

## State and error policy

| State/condition | Policy |
| --- | --- |
| Missing legacy mode | Valid; normal mode without write-on-read |
| Empty/omitted override | Valid; existing clear/preserve behavior |
| Populated normal/developer | Validate using persisted project policy |
| Malformed mode or numeric override | Explicit validation/data error; no truthy coercion or partial mutation |
| Non-Dev activation, unauthorized project, readonly, invalid CSRF | Existing denial envelope; state unchanged |
| Repeated authorized activation | Success, stays true |
| Unsupported disable request/payload spoof | Reject; no state change |
| Inactive MOFE/hourly | Existing retained-but-inactive settings and input eligibility |
| Working/failed/completed model | Existing status and inspectable artifacts; activation does not refresh historical results |
| Native version mismatch | Explicit failure before affected preparation; no fallback |
| Activation races normal preparation snapshot | Normal limits can reject elevated values; reload/retry |
| Archive restore / existing failed-fork recovery | Valid incoming true, false or legacy-missing state replaces destination mode without a mode-based denial; normal bounds resume when normal |

## Review and ancestry

Two independent read-only reviews and dispositions are retained beside this checkpoint. Resolve medium/high findings and obtain reviewer confirmation before accepting it. Before implementation, commit this checkpoint, canonical amendments and review artifacts as a standalone ancestor and record its SHA in the tracker. No implementation may be mixed into that commit. Commit authorization is not requested merely to finish this documentation task.
