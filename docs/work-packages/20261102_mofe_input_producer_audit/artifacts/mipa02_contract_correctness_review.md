# MIPA-02 independent correctness contract review

Reviewer: `/root/mipa_contract_correctness`; read-only, 2026-11-02.
Final disposition: PASS for bounded FC/HK checkpoint, no unresolved blockers.
Source remained `56e4fc293c1aa4c1654d0c24014e1f3a51a45b66`; no edits/builds/tests.

Medium finding resolved: original acceptance implied unsupported selected261029
9005/RAP cover behavior. Input reader misbinds extended header, reads restrictive
layer twice and applies lower-limit logic only to9003; specialized cover reader
is absent. Both contracts now preserve SOIL-02/COVER-01 native HOLD pending
separately reviewed reconciliation. Low finding resolved: preserve existing PMET
parse failures without promising validation of numeric fields on unmatched rows.
Primary disposition: accept both findings and amendments.

All active FC/HK references are in the six named files. Preserve arithmetic and
initialization timing. Direct probes must cover both daily lateral HK branches,
hourly FC thresholds and both DRAIN calculations where full histories do not
activate them. Selected PMET uses ntype (32/15000), correct mapped plant definition
and direct EVAPPM calls; obsolete checkout defects do not warrant production edits.

Residual gates: before/after dynamic ownership, both policies, unequal layers,
sub-0.95 powers, control/observer parity, numerical consequences, PMET role bounds
and transitions, clean matched build and exact final application/readback.

Reviewed canonical SHA256:
- WEPPpy: `3b1c7400a58c38c0c436f19747fee9a7e7ae0c09a439e0a5ea7d130270942cd7`.
- Native: `043b10c586b999faedf820a47c15588665cb14dbc86b66381c37818af5d725df`.
