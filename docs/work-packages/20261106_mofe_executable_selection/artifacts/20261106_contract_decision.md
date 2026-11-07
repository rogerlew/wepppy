# MOFE-EXEC-02 contract checkpoint

Prepared 2026-11-07 00:00 UTC (2026-11-06 Pacific).
Starting implementation revision: `51c84b612d870d44a728cb408f6c534ac49bf117`.

## Authority and classification

Operator instruction: "mofe wepp compatibilty should be ... independent of
whether its wbt or topaz. mofe topaz projects should have the same ... list of
wepp execs". This explicitly authorizes the behavior correction, and the subsequent operator instruction explicitly grants checkpoint and implementation commits, push, scoped tests, and wepp1 hotfix.

Applicable contracts: `docs/schemas/wepp-executable-selection-contract.md`,
`docs/schemas/nodb-persistence-concurrency-contract.md`, and
`docs/standards/contract-first-change-standard.md`. The first is amended; the
others remain unchanged. Classification: intended contract correction, since
the previous normative text incorrectly required WBT for executable selection.
Not an unchanged-contract conformance fix or an urgent-restoration exception.

## Delta and compatibility

MOFE releases depend on installed capabilities and input-reader requirements,
not the backend. Include legacy non-flattened and flattened presets without
graphs as well as Builder projects. Remove backend geometry filtering from
the executable choice calculation. Keep metadata validation and separate
geometry admission. Preserve stored geometry when constructing schema model
tuples; a selector that no longer filters backend cannot authorize pairs.
No persisted schema, model default, project backend, or config migration.

Incident evidence: the live web container reports installed MOFE releases
`wepp_260803`, `wepp_261010`, `wepp_261021`, `wepp_261026`, `wepp_261029`.
The incident run has `flattened=True`, `multi_ofe=True`, TOPAZ, no capability
graph, and no backend/representation axes. The shared policy returns `()`;
the run-page helper appends only saved `wepp_261029` for legacy display.

## Source boundary and failure class

Shared policy: `wepppy/nodb/wepp_binary_policy.py`. Confirmed consumers:
`wepppy/weppcloud/routes/run_0/run_0_bp.py`,
`wepppy/nodb/core/wepp_input_parser.py`,
`wepppy/microservices/rq_engine/wepp_run_payload.py`, and
`wepppy/microservices/rq_engine/schema_defaults_routes.py`.
The last also constructs model tuples and must independently preserve stored
geometry. Existing Builder creation restrictions are outside this amendment.

## Runtime states and regression evidence

- Absent optional graph/axes: valid legacy preset, including incident state;
  equal MOFE choices for TOPAZ/WBT, whether flattened or not.
- Present-empty installed compatible set: no eligible new binary; saved legacy
  display and unchanged submissions retain their contract.
- Populated graph/axes (v1 and newer): backend-independent binary enum while
  schema tuples and geometry admission retain stored-authorized pairs.
- Stored graphs with zero MOFE executable tuples: preserve canonical structural
  pairs using the existing structure relation, then populate newly installed
  compatible releases. Empty historic executable tuples do not remove geometry.
- Saved unavailable release: visible legacy state, not an eligible new choice;
  omission/current-value behavior preserved.
- Malformed graph or sidecars, hostile/unknown IDs: explicit existing errors
  before persistence or enqueue; not legitimate compatibility failures.
- Additional upload requirements: same backend parity, reader capability still
  required. Ordinary non-flattened single-OFE behavior remains unchanged.

Write failing regressions first; cover run-page choices, submission and schema
agreement, real parser save/reload and unchanged config/manifest. Run installed
sidecar validation without mocking its boundary. Verify the newly selected
release reaches prepared-run executable selection using an isolated TOPAZ/MOFE
fixture, and retain generated MOFE artifact evidence required by the canonical
contract before claiming full conformance. Run focused existing tests and
`wctl run-pytest tests --maxfail=1`; retain unrelated failures. Independently
review correctness before closure. Production deployment is not yet authorized
or claimed, and selection tests do not establish numerical model parity.

## Security and review

Low impact: no change to auth, CSRF, locking, executable path containment, or
sidecar integrity. Geometry authorization must remain separate and enforced.
Two independent read-only checkpoint reviews approved after disposition; see
`20261106_contract_reviews.md`. Operator authorized checkpoint and implementation commits, push, scoped tests, and wepp1 hotfix on 2026-11-06.
