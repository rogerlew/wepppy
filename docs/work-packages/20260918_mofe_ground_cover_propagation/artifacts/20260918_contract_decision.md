# Contract decision: MOFE-GROUND-01

Starting revision: `8dbf8f037`. Decision date: 2026-09-18 America/Los_Angeles.
Operator authorization: “okay. scaffold and execute work-package to correct the
ground cover propagation and validate on forest with equestrian-bonheur”.

Applicable contracts: [MOFE artifacts](../../../schemas/mofe-management-artifact-contract.md),
[NoDb persistence](../../../schemas/nodb-persistence-concurrency-contract.md).
RQ/API contracts are unchanged. Classification: intended behavior amendment;
the earlier MOFE contract explicitly excluded stored ground overrides.

Exact delta: apply saved `inrcov_override` and `rilcov_override` after disturbed
replacements per assigned segment; regenerate on either coverage edit; preserve
all three cover overrides on summary rebuild. Keep source defaults when absent,
RAP canopy precedence, single-OFE behavior and existing error/locking contracts.
Rationale: displayed ground selections currently fail to reach executed inputs.

Compatibility plan: no schema migration; existing absent attributes behave as
None. Previously inactive saved values become effective on explicit rebuild,
not deployment. Inspect selections before repair; rerun WEPP for fresh reports.
Security: low, no changed trust/access boundary; no new services or recovery
mechanisms. Source boundary: `wepppy/nodb/core/landuse.py` materialization,
segment plans, `modify_coverage`, and `build_managements` only.

## State and input matrix

| State/input | Outcome and evidence |
| --- | --- |
| Legacy missing or None override | Retain template/disturbed cover; real parser test. |
| Populated independent overrides, including 0 and 1 | Apply only selected fields/classes; combined and prepared parse. |
| Summary rebuild with retained classes | All cover selections survive, including zero. |
| RAP present | Existing canopy calculation wins; saved ground still applies. |
| Assignment absent or empty | Expected unbuilt state; build-first error before mutation. |
| Malformed populated assignment | Exceptional invalid build input; existing explicit builder failure. |
| Invalid cover name/value | Existing validation; no expanded accepted inputs. |
| Writer failure | Exception, no success; existing partial-file/retry semantics. |
| Single-OFE | Unchanged coverage workflow. |

Regression plan: extend actual-management tests plus scalar/process-pool tests;
prove failure before correction. On Forest use a supported fork of
`equestrian-bonheur`, exercise cover mutation and summary rebuild, inspect all
combined and prepared segments, execute WEPP with `wepp_260803`, and retain job,
source identity and output evidence. Verify source inputs/state unchanged.
Also verify existing browse/download access and canonical archive/restore byte
preservation on the disposable fork, never restoring over the source.

Review disposition: both reviewers identified the missing artifact lifecycle
acceptance. Added inventory, unchanged status/error semantics, browser/download
and archive/restore acceptance to the canonical contract and plan. Confirmation
received from both reviewers on 2026-09-19 UTC. Reviewer 1 also identified pre-existing configured cover-default build
ordering; excluded from this bounded repair, and Forest preflight must confirm
`cover_defaults_d` is None. No new default or ordering policy is authorized.

Independent readonly reviewers: `/root/ground_contract1` and
`/root/ground_contract2` both approve with no remaining blocking findings.
Forest preflight confirmed `cover_defaults_d=None`; source NoDb hashes retained
in validation evidence. Implementation/tests were not edited before review.
