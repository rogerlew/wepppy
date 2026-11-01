# Execution implementation prereview: second freeze

Disposition: **BLOCKED by a newly identified native COMMON collision; no execution approval.** Reviewed freeze SHA-256 `b025d8daf07dbaa5a8e0d757b100fc332ee7babb3a8011a87679c2c6bdc9e848`. No native build or run occurred.

The five findings in the initial execution review are closed in this revision: all three consumed prior public dependencies are bound, branch identity and direction are checked, aggregate history failure yields nonzero exit after retaining the panel, invalid physical states are separated from admissible signatures/ranges, and synthetic trace stocks must match the independent prior STATE/FINE reader. Full daily-gate coverage is also required. Actual clearing operands, native request precision and explicit zero-ST reconstruction semantics address the additional scientific findings.

Independently verified all frozen dependencies, including public files, prior raw inventories, compiler tools and runtime libraries. Read-only re-evaluation of the 16 retained malformed traces reproduced every recorded rejection; semantic traces confirm actual clearing despite stale entry FROZEN, unavailable branch suppression, negative NWFRZZ exclusion and use of the observed native request. No output files were written by these parser checks. Reader-controls-v2 receipt SHA-256 is `d51d0f289d9ace947ae01aa4d10283d6aefe39a4bc76c7122fc7be2b3bc25563`.

## Blocking helper collision

`fh_dump` includes `cwater.inc`, which declares native `FC(mxnsl)` in COMMON and types it REAL. The helper then declares `real uf,fc` and assigns `fc=0.0` and `fc=saxfc(i,iplane)`, intending a private scalar. That name resolves to the native FC array, not observer-only scratch storage. It is a duplicate type declaration and, if accepted by a compiler, a native-state assignment with incorrect WRITE payload shape. Either outcome violates the observational contract.

Rename the temporary consistently to an unmistakable private observer scalar, for example `fh_fc_obs`, covering declaration, both assignments and output. Retain prepared-v7 and this freeze as rejected, produce a fresh prepared revision and freeze, and verify the full helper local-name/assignment set against included native declarations. The direct name scan for the current helper candidates found FC as the collision; other reviewed candidate local names did not occur in native executable include declarations.

This finding supersedes the earlier inspection statement that all helper writes were observer-only. It was caught before any build or native invocation, so no run evidence is contaminated. Require independent review of the corrected prepared source and exact new freeze before execution.

## Bound analysis identities

- Declaration: `1d350bc2fdeb9036c53a67a7cf1acab78ae88ccf9dfea64f664b2843b61a3b82`.
- Reader: `10fdf713328edda69c16659a3ea43799a9e2c40f314bcb87035efd416d61140e`.
- Runner: `f6b11c75e10de1634f0dd198bc3d1edddd5fd284c53c6d5a2901d2fb2026dbaa`.
- Reader controls: `2d206fe20c89b31c3d46e0ffc21044a403afa263140b84982dc536fdd7b5d9ce`.
