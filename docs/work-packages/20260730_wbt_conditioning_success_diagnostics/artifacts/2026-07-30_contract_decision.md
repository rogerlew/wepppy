# DOM-05B Contract Decision: Conditioning Success Diagnostics

**Decision owner**: operator (`rogerlew`)
**Implementer**: Codex
**Approval venue**: current Codex thread; operator message received 2026-07-30
PDT: “scaffold and execute the package. commit and push weppcloud-wbt as part
of the work-package”
**Starting WEPPpy revision**: `c3deac7fab363bf1babe363019c88e2f8694b8c5`
**Starting WBT revision**: `b4d8774e3375ffd86a487c172f84e0d3f8a6cc50`

## Applicable Authority

- `docs/schemas/rq-response-contract.md`
- `docs/schemas/wbt-conditioning-diagnostics-contract.md`
- DOM-05 canonical field matrix at
  `docs/work-packages/20260728_channel_delineation_ui_contract/artifacts/field_matrix.md`
- `docs/standards/contract-first-change-standard.md`
- WBT tool contracts and existing TOPAZ diagnostics schema

The existing least-cost failure contract prohibits fallback fill in WEPPcloud.
DOM-05B preserves it: fallback diagnostics serve standalone WBT callers;
successful WEPPcloud least-cost output requires no unresolved low points and no
fallback.

## Normative Delta

1. Each successful WBT conditioning operation produces a versioned run-local
   JSON sidecar. It identifies the tool and status, records explicit units, and
   reports finite source-to-output maximum raise and maximum cut.
2. Method-specific data retains attribution:
   - Fill: filled depressions/cells/area/volume and maximum raise.
   - Breach: breached paths, maximum and longest cut, plus single-cell or
     residual fill effects.
   - Least cost: detected low points examined/resolved/unresolved, search
     distance, cut effects, and separately attributed fallback fill.
   - TOPAZ: depression fill, narrow-obstruction cut, and synthetic flat relief.
3. WEPPcloud validates the sidecar after a successful native exit. Missing,
   stale, malformed, mismatched, non-finite, or unsupported diagnostics stop
   the worker with a controlled error rather than silently reporting success.
4. RQ stores the reduced payload in job metadata, exposes it through aggregate
   polling, and publishes the base64url encoding defined by the diagnostics
   schema in the successful trigger. Paths and raw sidecar content are absent.
5. Both channel controllers show one plain-text completion paragraph in the
   ordinary status panel. Summary and detail are not duplicated.

## User Presentation Contract

Every method names the conditioning method and states:

- maximum terrain raise, including zero;
- maximum terrain cut, including zero; and
- the principal method-specific outcome in ordinary language.

Numbers use sensible display precision and the DEM elevation unit. The UI does
not label a magnitude safe, unsafe, acceptable, or excessive. Flat-routing
increments are separate from substantive fills/cuts.

Representative Fill wording:

> Fill completed. Terrain was raised by as much as 379 m; no terrain was cut.
> The operation raised 10.7% of the DEM while filling 46 depressions.

Representative least-cost wording without fallback:

> Breach (Least Cost) completed. Terrain was cut by as much as 6.9 m; no
> terrain was raised. Least-cost paths resolved 904 of 904 detected low points,
> and no fallback filling was used.

## Compatibility

The WBT CLI/wrapper arguments are optional. WEPPcloud always requests the
sidecar and operation id. Existing raster names, request parameters, persisted
NoDb state, RQ queue edges, and numerical conditioning behavior remain
unchanged. Trigger and aggregate status gain additive payloads older consumers
may ignore.

## Security

Security impact is high because this crosses a worker/subprocess/artifact/UI
boundary. Atomicity, confinement, operation identity, exact schema, transport
correlation, failure cleanup, and rollout/rollback rules are normative in
`docs/schemas/wbt-conditioning-diagnostics-contract.md`.

## Regression Evidence Required

- Stable output raster hashes with and without diagnostics for all four tools.
- Exact source-to-output extrema on the incident fixture.
- Tests for absent, malformed, stale/mismatched, and non-finite sidecars.
- RQ completion payload tests.
- Both channel-controller rendering tests proving text-only, nonduplicated
  presentation.
- Atomic write failure, path escape, retry freshness, stale writer, cross-job
  replay, polling, cleanup, and mixed-version tests.
- WBT runtime discovery/execution and installed-binary provenance.

## Rejected Alternatives

- Parsing WBT stdout: unstable and intended for human progress output.
- Post-processing only in Python: duplicates a full raster scan and cannot
  reliably attribute algorithm stages or fallback operations.
- A single changed-cell count: TOPAZ quantization/RELIEF and flat increments
  would obscure substantive terrain changes.
- Warning thresholds: no approved domain threshold exists and adding one would
  require an ADR.

Implementation conformance is pending the standalone checkpoint ancestor.
