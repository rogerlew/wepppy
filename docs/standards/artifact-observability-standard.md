# Artifact observability standard

Observability is paramount. Project inputs, intermediates, diagnostics, provenance,
failed/partial attempts, and completed outputs are user-facing project records.
They must be inspectable through established project tools and included in normal
archive/restore workflows. Filesystem visibility is not a completion flag or an
authorization mechanism. Communicate readiness, failure and freshness through
status/metadata; enforce access with the existing project authorization boundary.

## Required design and review gate

For every new or changed artifact-producing workflow:

1. Name a comparable existing module and reuse its layout/browser conventions.
   Put ordinary outputs in the module directory. Put attempt-specific artifacts
   in visible subdirectories with explicit status. Do not invent hidden storage,
   custom download-only access, or archive exclusions for project records.
2. Inventory inputs, work products, diagnostics, failed/partial states, outputs,
   provenance and their archive paths in the canonical domain contract.
3. Retain useful failure evidence. Cleanup may remove an empty coordination file
   or redundant successful copy, but must not destroy the only inspectable copy
   of a work product or diagnostic. Do not treat failed computation as permission
   to conceal or discard its artifacts.
4. Add executable regression coverage for visible paths and real filesystem
   failure behavior; assert archive member paths and byte-preserving restoration
   using the canonical archive implementation. Exercise the actual browser and
   download path under normal service identities before handoff.
5. Correctness and security reviewers must reject missing visibility/retention/
   archive evidence. A safety rationale cannot waive observability. A departure
   requires explicit operator approval of the exact files, reason and evidence
   retained elsewhere; record that decision in the canonical contract.

Credentials and secret material are not ordinary model artifacts and must not be
published. Use established secret storage. Coordination/cache exclusions must
name the exact class and demonstrate that no project record is lost; arbitrary
dot-file filters are not an acceptable record-retention policy. No new exceptions
are authorized by this standard.

## Enforcement

Root AGENTS.md and the correctness/security review templates require this gate.
The generated Artifact Observability CI workflow runs the domain writer,
failure, migration and archive tests on relevant pull requests and pushes.
Domain regression tests also run with the existing pytest suite; tests must exercise
writers and archive/restore, not merely assert documentation text. The Staley
observability tests are the first concrete conformance coverage. Authors must add
corresponding coverage when changing another artifact-producing workflow.
Review approval is blocked when that evidence is absent. A generic pathname
scanner cannot establish semantic retention and is not a substitute for tests.

A visible historical migration inventory may retain old path strings and exact
original metadata as audit evidence. Its physical files must remain visible and
archivable. Storage migrations must preserve payload bytes, audit path/hash
rebasing, and never silently bless changed science as current.
