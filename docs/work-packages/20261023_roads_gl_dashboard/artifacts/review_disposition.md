# Roads dashboard contract review disposition

Contract review only; no runtime conformance claim. Starting implementation:
`5227cb25831a1f86b2a70dd977d1cdad56a236cf`. Author/disposition owner: Codex parent;
independent reviewers: roads_dashboard_correctness, roads_dashboard_security,
roads_dashboard_ux. Operator approved D1–D4 and the output-scope switch before
this review. All initial findings remain in the reviewer artifacts.

## Findings

| ID | Severity | Disposition and canonical location | Closure |
| --- | --- | --- | --- |
| COR-01 | High | Accepted. Dashboard **Dashboard output-scope switch** and output-scope **GL Dashboard scope discovery** honor upstream mandatory resources: missing continuous summary invalidates scope; valid single-storm may lack mean-annual layer; typed-empty remains distinct. | Resolved; independently confirmed in the corresponding reviewer artifact. |
| COR-02 | High | Accepted. Dashboard **Integration and acceptance boundary** requires one guarded server materialization; **Coherent detachment view payload** specifies additive opt-in existing map view. Lifecycle crosslink preserves shared guard and ID-reuse rules. No new identity subsystem. | Resolved; independently confirmed in the corresponding reviewer artifact. |
| COR-03 | Medium | Accepted. Dashboard **Inputs, identity and provenance** names effective prepare `input_crs`, longitude/latitude output and conflict rejection; inferred/fallback CRS tests required. | Resolved; independently confirmed in the corresponding reviewer artifact. |
| COR-04 | Medium | Accepted. Dashboard **Display and interaction** and **Coherent detachment view payload** preserve nullable existing per-profile `segment_length_m`, label modeled source road-segment length, and prohibit substitution/summation of uploaded unsplit lengths. Decision artifact distinguishes persisted schemas from the additive opt-in response. | Resolved; independently confirmed in the corresponding reviewer artifact. |
| SEC-01 | Medium | Accepted. Dashboard **Integration and acceptance boundary** requires literal-text labels/details/table, safe constructed links and hostile-label browser tests. Computed metadata namespace cannot be overwritten by uploaded properties. | Resolved; independently confirmed in the corresponding reviewer artifact. |
| SEC-02 | High | Accepted; same correction as COR-02. Separate successful fetches cannot establish a coherent set across reused-ID re-preparation; require actual concurrent read/write acceptance. | Resolved; independently confirmed in the corresponding reviewer artifact. |
| SEC-03 | Medium | Accepted. Dashboard **Error isolation and cache behavior** isolates optional Roads errors from baseline; no shared poisoned latch, blanket non-OK-to-absence mapping or reload loop. Initial unavailable Roads keeps lifecycle status/code and authorized Baseline escape. | Resolved; independently confirmed in the corresponding reviewer artifact. |
| UX-01 | Medium | Accepted. Dashboard **Dashboard output-scope switch** disables incompatible map scenario/comparison controls while Roads is active, rejects incompatible restored state and re-enables controls in Baseline. | Resolved; independently confirmed in the corresponding reviewer artifact. |
| UX-02 | Medium | Accepted. Same section clears unsupported active graphs with an explanation, preserves supported graph choices and existing graph-specific semantics; Flow Duration remains baseline-only. | Resolved; independently confirmed in the corresponding reviewer artifact. |

## Rationale and scope containment

The coherent existing-map view is the smallest added read needed to address the
demonstrated race: independent component reads can each be valid yet belong to
different preparations with the same IDs. It reuses authorization and the Roads
shared guard, preserves ordinary geometry callers, and adds no service, persistent
identity, model change or schema mutation. Display-specific response fields are
additive and isolated behind an explicit view request.

No findings are dismissed or accepted as unresolved risk. Independent post-fix confirmations close all nine findings: four correctness,
three security and two UX. Canonical reviewed hashes are in the reviewer artifacts;
final editorial-status hashes are retained in review_manifest.json. Documentation
lint and diff checks pass. Commit/implementation/deployment remain separate gates.
