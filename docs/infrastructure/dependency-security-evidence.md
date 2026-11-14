# Manual dependency-security evidence collection

Production on wepp.cloud continues to use the installed `wctl` preset and
`scripts/deploy-production.sh`, with host-local Docker Compose builds. This
evidence utility does not build, publish, deploy, or approve an image.

The governing policy is [ADR-0140](../adrs/ADR-0140-dependency-security-gate-policy.md).

The operator-selected protected store is
`/workdir/weppcloud-deployments/.local/dependency-security/`. Raw reports must
remain private. CI collection requires a confirmed authenticated operator path
to the isolated runner and collection before cleanup. Authenticated SSH/SCP via
the existing trusted `runner-02` alias has passed a disposable fixture transfer
and private import. Collection of a CI-produced candidate bundle before cleanup
remains unvalidated. Do not upload raw reports to public-repository Actions artifacts.

## Import contract

The local importer accepts a manually collected directory, an existing private
destination directory, an expected image ID, and an independently retained
SHA-256 of `manifest.json`. The expected hash must come from the trusted
collection/review record, not be calculated from an untrusted bundle merely to
make it pass. Import success proves byte integrity and retention, not advisory
clearance, scanner correctness, freshness, or deployment authorization.

Manifest schema version 1 contains exactly `schema_version`, `image_id`, and
`files`. The image ID is `sha256:` followed by 64 lowercase hexadecimal digits.
`files` is a nonempty object keyed by flat filenames; each value contains exactly
`sha256` and `size_bytes`. Names are restricted to ASCII letters, digits, period,
underscore and hyphen, start with a letter or digit, and cannot be
`manifest.json`. Reports must be collected as regular files, not symlinks or
directories. Every directory member must appear in the manifest except the
manifest itself. Empty or additional files, malformed JSON, duplicate JSON keys,
identity mismatch, and hash/size mismatch fail explicitly.

The importer streams files into a new 0700 staging directory in the destination,
creates files as 0600, verifies hashes and sizes, and atomically publishes the
directory beneath an exclusively reserved manifest-hash directory. Only its
`bundle/` child plus a successful importer exit and readback proves completion;
directory existence alone is insufficient. It rejects an existing target instead of
overwriting retained evidence. Failure removes only its own staging and reserved
directory. A crash can leave an incomplete reservation requiring operator review;
it must not be treated as a retained bundle without a successful import receipt.
The destination must already be
owned by the invoking user with mode 0700. Caller-selected roots resolve once
(including the established `/workdir` alias), then traversal and artifact reads
use held directory descriptors without following symlinks.

Example invocation after authorized manual collection:

    python3 tools/security/import_dependency_evidence.py \
      --source /private/collected-bundle \
      --store /workdir/weppcloud-deployments/.local/dependency-security/evidence \
      --expected-image-id sha256:<64-hex-image-id> \
      --expected-manifest-sha256 <independently-retained-manifest-hash>

The importer is a component under validation. The scanner producer, CI wiring and Compose pre-activation hook remain open;
the standalone policy evaluator is described below.
The existing npm workflow now runs `wctl run-npm lint` before `wctl run-npm test`;
this does not constitute the isolated candidate-image security workflow.
For local candidate test-image selection, see the
[isolated Python CI runtime](../../docker/README.md#isolated-python-ci-runtime).
Ordinary CI evidence requires 90-day retention; activated-image evidence requires
at least 365 days and the entire rollback-eligibility period. The importer does
not implement deletion or infer which images have been activated.

## Policy evaluator and retained candidate activation

Run `python -m tools.security.evaluate_dependency_evidence --help` from the
repository root for the standalone verifier. It requires an independently
trusted manifest hash, approved policy/disposition hashes, and exact candidate
source/image/lock identities. Never derive approval arguments from the candidate
bundle itself. Exit 0 means the supplied evidence passed this component; it is
not deployment authority. Exit 1 reports blocking findings; exit 2 means invalid
or incomplete evidence.

The canonical deploy script separates build from activation for the full stack,
worker stack, and dedicated wepp3 fork/archive worker:

```bash
scripts/deploy-production.sh --build-retained-candidate
# collect/import evidence and publish the independently reviewed approval
scripts/deploy-production.sh --resume-retained-candidate \
  /workdir/weppcloud-deployments/.local/dependency-security/candidates/<host-id>/<candidate-id>/receipt.json
```

Build mode performs the no-cache build and runtime validators, atomically writes
the private receipt/configuration/immutable-ID override, and exits without RQ
fencing or service stop. Resume derives its approval path from the protected
store and receipt hash; no evidence or approval path is accepted from CLI or the
candidate. It drains under the owned RQ fence while known-good containers remain
running, reruns the complete gate, activates only receipt `sha256:` IDs with
pull/build disabled, and restores the exact pre-cutover image map on later
failure. Generic `--skip-build` remains rejected.

Provision the operator-owned authority once with a restrictive umask. Do not run
these commands as a different account from the deployment operator:

```bash
umask 077
install -d -m 0700 \
  /workdir/weppcloud-deployments/.local/dependency-security/{candidates,evidence,approvals,activations}
install -d -m 0700 \
  /workdir/weppcloud-deployments/.local/dependency-security/approvals/dispositions
```

After independently reviewing the exact evidence and disposition JSON, store the
disposition as `approvals/dispositions/<sha256>.json` with mode 0600. Publish the
approval atomically through the repository tool; never hand-author the derived
approval pathname:

```bash
python3 tools/security/retained_candidate.py publish-approval \
  --project-root /workdir/wepppy \
  --receipt <candidate-receipt-path> \
  --evidence-bundle <private-imported-bundle-path> \
  --evidence-manifest-sha256 <independently-retained-manifest-hash> \
  --dispositions-sha256 <reviewed-disposition-file-hash> \
  --approver <operator-identity> \
  --review-trigger "new advisory, evidence, configuration, or candidate identity"
```

The tool validates canonical roots, ownership, modes, manifest/disposition
hashes, and the current policy hash before exclusive 0600 publication. Resume
then revalidates the record and runs the evaluator. Successful activation writes
an immutable ledger below `activations/<host-id>/` and protects the prior image
IDs with retained rollback tags so ordinary Docker pruning cannot remove them.

On wepp3, resume acquires the same global dequeue fence, drains only the
`fork-archive` started registry while the known-good worker remains online,
rechecks the exact running image immediately before warm shutdown, and requires
the restored or candidate worker to run as `1002:130` with exactly one current
`fork-archive` registration. Targeted CAP remains on its distinct excluded-image
recovery contract. Targeted web and targeted batch/source-overlay/rollback
common-image activation remain fail closed until their retained scopes are
implemented and reviewed. A passing resume gate is not M5 rollout authorization.

## Collector qualification (not yet wired)

`python -m tools.security.collect_image_evidence --help` describes the current
producer. It requires an exact image/source and an independently hashed clean
build receipt binding the static-builder lock. It snapshots the pinned scanner
binaries and approved scientific config/manifest. A never-started container export
is read by the retained trusted parser; candidate Python is never inventory
authority. No archive content is extracted or executed.

The producer records failed commands privately and publishes a bundle manifest
only after required collection stages complete. It does not approve advisories.
The evaluator requires the exact scientific input hashes, retained trusted parser,
verified-file count, image/source/build/lock binding, raw scans and database.
The output directory must be new; each attempt retains its own records. Recovery
after abrupt interruption is limited to the exact uniquely named never-started
container recorded by that attempt, never broad container or image pruning.

The scanner carrier is the same immutable, source-addressable Node image pinned
for npm collection. Syft and Grype remain separate hash-pinned static
executables mounted read-only. Do not replace the carrier with a local Docker
image ID: local IDs cannot be pulled after pruning. The recovery rationale and
production-host version readback are recorded in
`../work-packages/20261110_wepp1_dependency_security_gate/artifacts/20261114_scanner_carrier_recovery.md`.

Complete real-image producer qualification, CI integration, production-host
receipt creation, evidence approval and production-equivalent recovery remain
open. The canonical deploy integration is implemented but not yet authorized for
M5 rollout. Ordinary `--skip-build` has not been weakened.
