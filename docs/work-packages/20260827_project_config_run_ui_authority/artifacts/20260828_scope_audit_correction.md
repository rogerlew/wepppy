# Ratified WP12D scope audit correction

**Amendment**: `PC-24/WP12D-20260828-4`

**Status**: ratified by the project operator on 2026-08-28

**Audit range**: documentation checkpoint `596ff5758` through technical Forest
candidate `588608f1a`

**Behavioral contract change**: none beyond the already reviewed and Forest-
validated implementation

## Audit result

The scope-versus-changed-files comparison maps every changed configuration and
production consumer to the ratified WP12D boundary except the following three
support entries:

1. `wepppy/nodb/locales/__init__.py` is export-only. It reexports
   `capability_structure_payload` and `capability_structure_sha256` from the
   already-ratified `capability_graph.py`; it owns no runtime decision.
2. `wepppy/nodb/locales/capability_structures/README.md` and
   `wepppy/nodb/locales/capability_structures/catalog.json` are the directly
   required append-only reader-floor structure authority and its maintenance
   contract. The ratified behavior requires this checked-in catalog but the
   exact source list named only its loader.
3. `wepppy/microservices/rq_engine/auth.py`, with regression coverage in
   `tests/microservices/test_rq_engine_auth.py`, contains the Forest-required
   identity-handoff correction. The sanitizer now prefers the existing signed
   numeric `user_id` claim and retains numeric `sub` fallback. JWT signature,
   audience, revocation, scope, request-time owner/Admin/Root authorization,
   and privileged-role allowlisting are unchanged.

The remaining changed paths are one of:

- an exact ratified implementation/config consumer;
- a test for the ratified validation matrix;
- required generated RQ dependency evidence;
- a work-package review, execution, or Forest acceptance artifact; or
- the controller developer README required by the repository documentation
  contract.

No unrelated dirty-path exclusion was staged. The Config Builder links,
Interfaces template, feature registry, and production deployment paths remain
unchanged by WP12D.

## Exact correction

Amendment `PC-24/WP12D-20260828-4` adds only the three entries above to
WP12D's changed-consumer/support list. It preserves all existing commits and
evidence, including:

- reader floor `80f4810b7`;
- worker-load hotfix `326f2138c`;
- identity-handoff correction `924813874`;
- provenance-settlement candidate `588608f1a`; and
- Forest writer/rollback acceptance in
  `20260828_writer_forest_acceptance.md`.

The correction does not authorize new code, broader authentication behavior,
merge to `master`, or production deployment. The exact scope comparison and
this correction must be carried into parent WP12 promotion review.

Independent correctness and security reviews of the identity correction are
READY with High 0, Medium 0, and Low 0. Security confirmed that malformed or
missing numeric identity remains fail-closed, PowerUser is not promoted, and
public job information does not expose queued actor metadata.

## Ratification record

The project operator ratified the correction exactly as documented on
2026-08-28 with this statement:

> I explicitly ratify amendment PC-24/WP12D-20260828-4 exactly as currently
> documented, preserving all existing commits and carrying this scope audit
> into WP12.

This record closes the WP12D scope exception. Parent WP12 must retain this
artifact and repeat the scope-versus-changed-files comparison before canonical
merge or production promotion.
