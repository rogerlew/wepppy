# Security review — RUPC-01

Date: 2026-11-17 UTC. Independent reviewer: `/root/contract_review_b`.
Impact triage: high (native input/file workflow). Scope: checkpoint `8e87b2363`
and implementation diff; no auth, secrets, queue, privilege or deployment change.

## Findings and resolution

SEC-01 (medium): repeated all-pairs connected-component scans after noding allowed
small valid uploads to occupy a worker for excessive time. Replaced with endpoint
adjacency traversal; existing Shapely STRtree narrows conflicting-input and source
membership queries. Regression covers a 24x24 grid. Independent measurements:
16 features 0.037 s; 32 features 0.144 s; 48 features 0.335 s; 96 features 1.521 s.
The former 32-feature case took 16.931 s. No new dependency or arbitrary rejection
of valid roads. Finding closed; this is not a universal GEOS resource bound.

Finite input values could overflow area products. Explicit finite target/emitted/
aggregate area checks and regression tests close that robustness finding.

## Boundaries and valid-state noninterference

Native output names use controlled numeric hillslope IDs. Existing run locking,
retention, workspace containment and publication are preserved. Stale admission
precedes mutation/model execution. Shared source membership is validated against
prepared geometry; canonical profile tables do not duplicate accounting rows.
No new shell interpolation, external egress or authorization surface was added.

The isolated validation service uses the existing forest image, uid 1000, gid 993,
groups [993], umask 0022 and existing mounts/environment, with only the candidate
checkout substituted. The running application checkout was not remounted. Source
baseline/upload hash equality and retained failure/native geometry evidence pass.
The temporary Compose file containing runtime environment is mode 0600 outside
Git and is removed with validation-container teardown.

## Verdict

Reviewer confirmed pass on the inspected diff, no unresolved medium/high findings.
Native receipts and 191 scoped tests support the changed boundaries. No production
deployment is authorized by this review. Ordinary source areas and lifecycle
contracts remain controlling; no switchback connectivity safety claim is made.
