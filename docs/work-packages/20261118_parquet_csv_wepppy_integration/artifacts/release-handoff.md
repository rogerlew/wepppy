# Native CSV release handoff

Implementation is local to `codex/parquet-csv-cli-package`; no production service
has been changed. Integration history follows the standalone M0 checkpoint
`a1f40de48`, dictionary amendment `3fefd089d`, and width amendment `9a4642a01`.

## Release gate

After authorized source integration, use the installed host wctl preset and
`scripts/deploy-production.sh --build-retained-candidate`. The canonical entry
point builds locally and runs the native CSV validator before any service stop.
Follow the existing retained-candidate evidence and activation procedure in
[dependency security evidence](../../../infrastructure/dependency-security-evidence.md#optional-strict-scan-evaluator-and-retained-candidate-activation),
then resume the exact retained receipt through the same script. This document
neither grants deployment approval nor replaces existing release gates.

The validator performs an actual installed native conversion and eight-worker
browse HTTP byte readback under the configured browse UID, with an isolated
read-only synthetic run mount. It also verifies raw bytes and private-project
denial. Fixture permissions are independent of operator umask; build-only scratch
is removed from the image so runtime UID selection remains supported.
Local image evidence is not production secrets, filesystem or proxy validation.
On the target host retain its resolved UID/GID/groups, mounts, umask, configuration
and immutable image identity; verify an authorized real-project CSV download and
raw readback under that configuration before claiming production acceptance.

## Operation and rollback

CSV export is on demand and temporary. Original Parquet is retained. There are no
CSV environment settings or fallback backend. Two shared slots cover staging,
conversion and serving; busy returns 503 with Retry-After. Correlated logs retain
outcomes, input/output hashes, sizes and resource metrics without cell/filter data.
See the [integration contract](../../../schemas/parquet-csv-integration-contract.md)
for fixed budgets, type support, errors and strict protocol v2.

Never unlink live slot lock files or delete active request directories. A new
request reclaims a fixed directory only after acquiring its persistent lock.
Cleanup failure retains capacity and is logged; investigate ownership, filesystem
and child exit before recovery. Restarting a browse worker is not permission to
remove another worker's active conversion. No project CSV cache is introduced.

Rollback is a whole release through the canonical retained-image recovery path.
Restore matching prior source/deployment entrypoint and exact prior image map;
do not pair the new required-native gate with an older image lacking the CLI.
Preserve the deployment ledger and retained rollback tags. No registry pull,
backend flag, Redis flush, volume deletion or ad hoc Compose topology is added.
After recovery, repeat authorized CSV/raw readback and authorization checks.
