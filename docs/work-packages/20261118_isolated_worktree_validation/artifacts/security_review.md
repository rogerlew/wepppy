# Security review: isolated-worktree validation

Reviewer: Codex primary integrator (self-review, not an independent review).
Date: 2026-11-18 UTC. Branch: codex/isolated-worktree-validation.
Scope: worktree CLI, container prerequisite checks and retained receipts.
Security impact: high because the tool selects container mounts and executes
candidate code. Contract: tools/wctl2/docs/worktree-tests.md.

## Threat model and valid states

This is a trusted local developer CLI, not a sandbox for hostile candidate code.
It retains the existing development service's identities, network and environment.
A supplied dependency checkout is trusted code; metadata checks establish lock
compatibility, not a cryptographic attestation of every installed package byte.
Explicit donor paths are optional when candidate/image prerequisites already
exist. Missing or stale required artifacts must reject before pytest.

## Findings and resolution

- Compose run does not support Docker run's `--mount` flag. Real execution caught
  this before tests; use supported `--volume` after verifying sources exist.
- Reject colons/commas in mount paths so the volume grammar cannot inject fields.
  Subprocess arguments remain arrays; the container command uses shlex.join.
- Strip ambient Git redirection variables from common-directory discovery while
  retaining CLIContext environment settings. Compose project selection must not
  override default caller checkout selection; both explicit and default source
  selection are regression tested.
- Native binary/sidecar validation alone cannot establish source compatibility.
  Compare complete Cargo/source inventory and exact candidate hashes as well.
- Read-only container mounts do not freeze donor files on the host. Recheck
  recorded runtime file hashes after pytest and return failure on changes.
- Database exception strings can contain credentials/SQL parameters. Translate
  SQLAlchemy errors to class-only diagnostics; report missing column names only.

## Surface checks

Auth/session/CSRF and RQ wiring: unchanged. The profile test fixture registers
existing account context helpers/blueprint and preserves its CSRF assertions.
No new application route, privilege, token or authentication mechanism exists.

Filesystem: candidate bind is writable by the existing service identity; Git
metadata and explicitly borrowed dependencies are read-only. Missing source
paths cannot become Docker-created directories. Receipts are uniquely reserved;
prior evidence is never overwritten. Generated output comes from candidate
source. Source mutation is reported and left visible, never reset silently.

Subprocess/network: canonical Compose helper, no dependency startup, image pull,
service ports or rebuild. Parser version checks and actual Chromium launch run
inside the one-off container. No new external dependency or service is added.
Canonical wctl installer bootstrapped its existing Typer/Click dependencies in
this worktree; the test command itself installs nothing.

Database: inspect model columns inside a read-only transaction with statement
timeout. No schema creation, migration or permissions change. Application import
is the existing configuration path. Missing columns reject before pytest.

Data integrity: nonce verifies live source; before/after fingerprints include
tracked/untracked nonignored code/config/templates, missing files and symlink
targets. This is not a concurrent-edit lock or a detector of reverted transient
writes. Shared service isolation still belongs to each integration test.

## Evidence and verdict

The complete wctl suite passes, including actual temporary-Git/source mutation,
receipt overwrite rejection, mount grammar, stale locks and stale native source
checks. Real one-off native and browser suites pass with compatible read-only
assets. Real broad preflight aggregates missing prerequisites and rejects the
stale database before collection. See validation.md and retained receipts.

Gate: pass for this trusted CLI scope. No unresolved medium/high finding.
No deployment or independent-review claim. Rollback: revert task commits; no
shared service or schema repair is required. Developer receipts are exposed by
printed paths and retained selected artifacts; they are not project-run outputs.
