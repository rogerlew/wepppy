# Manual dependency-security evidence collection

Production on wepp.cloud continues to use the installed `wctl` preset and
`scripts/deploy-production.sh`, with host-local Docker Compose builds. This
evidence utility does not build, publish, deploy, or approve an image.

The governing policy is [ADR-0140](../adrs/ADR-0140-dependency-security-gate-policy.md).

The operator-selected protected store is
`/workdir/weppcloud-deployments/.local/dependency-security/`. Raw reports must
remain private. CI collection requires a confirmed authenticated operator path
to the isolated runner and collection before cleanup; that path is not yet
established. Do not upload raw reports to public-repository Actions artifacts.

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
      --store /workdir/weppcloud-deployments/.local/dependency-security/imports \
      --expected-image-id sha256:<64-hex-image-id> \
      --expected-manifest-sha256 <independently-retained-manifest-hash>

The importer is a component under validation. The scanner producer, policy
evaluator, CI wiring and Compose pre-activation hook remain separate open work.
The existing npm workflow now runs `wctl run-npm lint` before `wctl run-npm test`;
this does not constitute the isolated candidate-image security workflow.
For local candidate test-image selection, see the
[isolated Python CI runtime](../../docker/README.md#isolated-python-ci-runtime).
Ordinary CI evidence requires 90-day retention; activated-image evidence requires
at least 365 days and the entire rollback-eligibility period. The importer does
not implement deletion or infer which images have been activated.
