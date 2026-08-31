# WP08 Security and Correctness Review

**Reviewed**: 2026-08-26
**Disposition**: Approved; no unresolved findings

## Boundaries reviewed

- Availability requires JWT run-read access and remains read-only.
- Preview and enqueue require a user actor who is the current project owner or
  has Admin/Root authority; public-run access and session/service actors do not
  confer mutation authority.
- The enqueued job retains only the sanitized actor identity and relevant
  privileged roles. The worker reauthorizes that actor against current project
  ownership before touching either artifact.
- Apply binds an opaque preview identity to the current config bytes, manifest
  bytes, and complete ordered additions, and separately requires a trigger
  present in that reviewed delta.
- Manifest and materialized config secret scanners reject unsafe input and
  output. API and job responses expose digests and counts, not filesystem paths
  or config contents.

## Integrity and concurrency review

- The resolver reconstructs only the manifest-recorded builder or preset chain
  and rejects inactive, ambiguous, malformed, or unknown sources.
- Merge logic adds missing keys only. Existing values, including user changes,
  are never overwritten, and a digest mismatch is accepted as provenance
  rather than treated as permission to replace content.
- One project lock serializes recovery and mutation. A persisted journal binds
  complete prior/result config and manifest images to hashes before the first
  replacement. Recovery does not consult mutable registry sources.
- Fault-injection coverage exercises journal commit, config replacement, and
  manifest replacement boundaries. Concurrent same-delta applies produce one
  amendment; stale and authority-loss paths produce no mutation.
- Redis single-flight reservation is released if enqueue fails and by the
  worker on every terminal path. The filesystem lock and preview revalidation
  remain the authoritative deduplication boundary.

## Residual risk and rollout

The worker reservation has a bounded TTL; an exceptionally long job could lose
that advisory Redis marker. This does not permit duplicate mutation because
the project lock and opaque preview revalidation reject the second apply. The
backend remains disabled by default through
`WEPPPY_PROJECT_CONFIG_UPDATE_ENABLED`; WP09/WP10/WP11 own later UI, lifecycle,
and promotion gates.
