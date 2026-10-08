# Independent contract review A

Reviewer: prism_contract_review_a (read-only implementation review).
Reviewed at: 2026-10-08T22:40:25Z.
Starting implementation revision: `199fa5b1ea74e715804467849535205f2a13acc0`.
Review scope: proposed PRISM contract, ADR-0082, lineage amendment, checkpoint
and plan, with current climate/CLIGEN/catalog and capability source inspection.

## Findings

1. **High — omitted canonical capability authority.** The checkpoint's applicable
   contract list and source boundary omit
   `docs/schemas/project-owned-config-contract.md`, although the PRISM contract
   requires Builder metadata to agree with the new run-menu dataset. Section
   7.2.2 (current Continental-US row at line 539) enumerates the current climate
   envelope, and the acceptance list at line 2230 requires its exact matrix.
   Sections 7.2.2 and 9 also preserve existing stored graph authority and frozen
   historical Builder response members. Implementing only `climate_catalog.py`
   leaves live capability-authoritative menus unable to offer PRISM; broadening
   all stored graphs would violate backward compatibility. Amend and cross-link
   the current CONUS matrix with explicit `observed_prism_800m` method/default
   relations, provider identity and graph compatibility. Include the finite
   locale-profile/capability/Builder integration boundary and tests in the
   checkpoint. Keep old v2 and stored v3 envelopes unchanged unless an existing
   explicit refresh is requested. Other locale matrices remain unchanged.

2. **Medium — numerical acceptance promises exceed the specified PRN path.**
   `prism-historic-climate-contract.md:15` selects the established PRN writer,
   but line 23 requires precipitation and temperature parity at CLI rounding
   precision. `wepppy/climates/cligen/cligen.py:675` rounds precipitation to
   hundredths of an inch (0.254 mm) and temperatures to whole Fahrenheit
   degrees before generation. These errors exceed CLI's 0.1-mm/0.1-C rounding;
   trace source rain can become a dry generated day. Specify source-to-PRN
   quantization separately from PRN-to-CLI rounding, retain transformation
   diagnostics, and qualify wet/dry-calendar assertions at the representable
   PRN/CLI precision. Alternatively, a source-restoration algorithm needs a
   separately explicit treatment of storm structure on rounded-to-zero days.
   The smallest compatible resolution preserves the existing PRN semantics.

## Other assessment

- User authority covers the described integration, both multiple methods,
  target-run execution and dev Compose restart. The checkpoint records that
  approval and the earlier commit authorization. No implementation edits were
  present during this review; the ancestor commit gate is still pending.
- Additive enum 16 avoids the existing Daymet mode 9 and stochastic mode 5.
  Full completed years and explicit provider/masked-cell failure avoid padded
  invented weather. No new queue or authentication surface is proposed.
- The contract covers absent, empty, populated, legacy, malformed, failed and
  archived artifact states. It retains raw sources, separate transformations,
  rejected candidates and archive portability; staged centroid/revision
  failure semantics agree with the amended lineage contract.
- The final dewpoint formula is adequately specified, but tests must include
  colder as well as warmer revised hillslopes: re-clipping already-clipped
  centroid dewpoint is not `max(raw tdmean, final Tmin)` when Tmin falls.
- Existing scaling may further change final precipitation; parity evidence
  should distinguish adapter output, monthly revision and final scaling.
- Read-only review cannot establish lock/publication/permission conformance or
  native CLIGEN/WEPP execution. The planned unmocked publication, source
  archive/restore and prepared `wepp/runs` checks remain acceptance gates.

## Verdict

**Changes required before checkpoint commit and implementation.** Resolve the
two findings above, obtain post-fix confirmation, then record the standalone
checkpoint revision and preserve its ancestry. No implementation is approved
by this initial review.

## Post-fix review

Reviewed at: 2026-10-08T22:41:59Z; implementation HEAD remains
`199fa5b1ea74e715804467849535205f2a13acc0`.

Both findings are **resolved in the proposed contract checkpoint**:

- The new Project Config amendment explicitly adds only PRISM to current live
  CONUS authority, names both structural identities, preserves existing stored
  v2/v3 graphs and historical response members, and requires a standalone
  reader-first deployment before new writers. The checkpoint registers the
  canonical owner and finite locale/capability source boundary. Direct JSON
  comparison of the retained candidate against existing structure `3151e7e...`
  found only the added PRISM axis member, two method relations and two defaults.
  Independently recalculated canonical SHA-256 equals the declared
  `2c2934682af720fac7d022aa22f830087a10f2f423e4cb329d2a23c88c6ef1d3`.
- The PRISM contract now separates PRN quantization from CLI rounding, requires
  trace-rain diagnostics, qualifies wet-day identity and disallows adding trace
  rain to zero-duration storms. It also explicitly recomputes revised dewpoint
  from raw source rather than the clipped centroid value.

**Verdict: approved for the standalone pre-implementation checkpoint.** No
unresolved high or medium contract finding remains. This approves intended
behavior and evidence requirements, not implemented conformance. The checkpoint
commit must still precede code edits; reader deployment, historical/new graph
reopening, raw-to-PRN-to-CLI numerical checks, true publication failures,
archive portability and both live WEPP spatial methods remain required. Record
the actual reader revision in place of the candidate's pending placeholder
before writer exposure. Implementation review must verify unchanged default
station/seed behavior and distinguish pre-scaling versus final model parity.
