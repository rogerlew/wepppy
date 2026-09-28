# SUDI-03 contract decision

Starting revision: 50495bfeebf5ccf3c8cf50753100803e35bb5382.
Operator explicitly requested 7777 support; earlier commit authority persists.
Intended additive behavior change, not a conformance repair.

Amended authority: docs/schemas/single-user-defined-inputs-contract.md (Upload
interface and validation), docs/adrs/ADR-0075-single-user-defined-inputs.md.
Unchanged shared contracts: RQ response/error, CSRF, NoDb persistence/concurrency,
MOFE management artifact, WEPP run input, and Pure controller presentation.
No request fields, metadata keys, enums, source lifecycle or auth changes.

7777 uses eight header fields, ten layer fields (no layer anisotropy), and a
three-field restrictive record carrying profile anisotropy. Preserve values,
version and ksflag; retain existing modifiers. No migration or inference.
Existing versions and legacy serializer defaults remain unchanged.

Security: strict shape/numeric validation before permissive WSU; extend hostile
syntax/count/numeric tests and valid layer-boundary tests. Fresh upload creates
source; valid populated upload replaces/reuses; empty without source errors;
malformed upload retains previous source. Existing lifecycle checks and visible
working/failed/completed states remain unchanged. Regression tests inspect raw
source hashes and all generated OFE values, invoke native executable through32
OFEs, and exercise source publication plus authenticated multipart transport.
Archive/restore uses unchanged opaque immutable source handling; include7777
source retention evidence where available.

Review disposition: distinguish WEPPcloud field preservation from existing native
reader calculations/limits. The supplied /tmp/boulderck_mica_1_7777.sol contains
2400 mm depth; retain it in prepared input, acknowledge native1800 mm internal
cap, and execute the exact supplied source as an additional acceptance fixture.
