# RUPC-02 top-placement contract checkpoint

Status: amended contracts accepted; both independent reviews pass; code unchanged.
Starting implementation: `e6989a622f7aea86126d098f48e2e57c15f35b61`.
Branch: `work/roads-unrutted-strip-contract`.

## Authority and rationale

2026-11-17, Roger Lew in the Codex conversation asked about placing the eight
infeasible crossings at the hillslope top, then directed: “let's add to the current
work-package / branch. update the work-package and proceed with the contract
ammendments”. This authorizes the top-placement amendment. Original native failure
evidence is preserved. Terrain distance and representative profile length can
disagree; rejecting non-positive upstream length is a policy limitation rather
than proof of impossible terrain geometry.

## Normative delta and inventory

`docs/schemas/roads-unrutted-strip-contract.md`, section RUPC-02, defines the exact
trigger, road/fill fit, two/three-OFE roles, downhill area adjustments, short-landuse
exception, provenance and execution-policy marker. ADR-0146 records rationale,
alternatives and scientific limitations. Roads specification and canonical baseline,
settings, preparation-lifecycle and water-accounting contracts link the amendment.
Existing output-scope, NoDb persistence and RQ contracts remain unchanged.

## Compatibility and regression plan

Additive summary/manifest fields only; no key removal. Keep prepared geometry
policy v1, invalidate old execution as current via the placement policy marker,
require rerun rather than reprepare, retain old artifacts. Native role transforms
must consume actual road/fill/landuse order, including a new road/fill-only shape.
Original valid positive-upstream behavior stays unchanged. Area remains invariant;
modeled runoff from above a top-placed road is zero and must be disclosed.

The scoped acceptance matrix adds boundaries, short downhill landuse, exact fit,
oversized road/fill, downstream remainder handling and lifecycle states. Native
writers, contributor runs, replacement PASS and watershed consumers require direct
evidence on the disposable forest run, with all eight prior failures dispositioned.
No new test execution is claimed by this contract-only checkpoint.

## Security and review

Existing run authorization, paths, locking, archive and process boundaries stay
unchanged. Dedicated review remains required for native/file and current-result
boundaries; malformed dimensions must not trigger an adjustment that bypasses
validation. Independent reviews and dispositions will be recorded below before
checkpoint commit. No runtime implementation edits precede the checkpoint.

## Independent review disposition

Review A (`/root/contract_review_a`, correctness): pass after clarifying the
single summary marker and mixed/empty applicability, adding the new failure to
the closed specification enum, and separating downstream compensation provenance.
Final verdict: no remaining blocking findings.

Review B (`/root/contract_review_b`, security/noninterference): pass after closing
R2-SEC-01 (medium). The contract now explicitly admits old archives as historical,
checks marker/row consistency only for affected designs, and covers mixed/empty
attempts without weakening completion checks. No remaining medium/high findings.
Both reviews were read-only and independent of the amendment author.

Validation: scoped Markdown lint and ADR-date checks pass; `git diff --check`
passes. Spelling preview retained unrelated existing prose and tool names. No
runtime files changed or implementation tests executed for this checkpoint.

Review disposition recorded: 2026-11-17T18:31:59.672633+00:00 UTC.
