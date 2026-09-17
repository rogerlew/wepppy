# NoDb hydration generation conformance wave

Status: independent correctness/security checkpoint PASS; no NoDb implementation edits yet.

SEC-M1-01 demonstrates `_hydrate_instance` and `load_detached` returning payload
A tagged with replacement B's mtime/size when `os.replace` occurs during decode.
The unchanged NoDb persistence contract requires disk-authoritative hydration,
cache signature validation and stale-write rejection. Pairing A with B's version
violates those obligations even for ordinary atomic writers.

## Bounded correction

Add a read-snapshot helper to existing `_read_retry`: open once, read the text,
retain that descriptor's stat, and compare device/inode/size/mtime_ns
across the read. Ctime is deliberately excluded: removing the old path during
atomic replacement may change ctime without altering the opened bytes. Return text and descriptor stat together through the
existing initial-read retry boundary. Both loaders assign tracked mtime/size
from that returned stat, never a later pathname stat after decoding. A concurrent
atomic replacement may leave a complete earlier payload associated with its own
earlier signature; next cache reuse and dump compare against current disk and
must reject/refresh it. No whole-object merge, new lock, hash cache or global
cache clear is introduced.

Preserve NoDb JSON schema, Redis payload behavior, read-only/detached semantics,
initial optional absence and required-read errno behavior. Detected read-time
mutation raises ESTALE through the existing bounded initial-read policy;
ordinary reads outside that context still do not retry. Preserve all writer
atomicity, permission, fsync and post-commit contracts.

## Validation and scope limits

Turn the retained two-loader real `os.replace` probe into a regression: A is
never tagged as B, cache validation must report a mismatch and the usual stale
write guard must remain effective. Test optional absence, normal snapshots,
in-place detectable changes and scoped retry behavior. Run NoDb targeted/stub
gates and full sanity. Existing cooperative writer monotonic mtime remains the
cache/write identity contract; unrelated out-of-band preserved-time edits and
Redis cache-key expansion are not silently added to this wave. No generated
scientific artifact schema changes.

Independent reviewers must confirm the conformance classification and bounded
remedy before this wave begins. Keep the separate first-wave content-currentness
review and runtime acceptance gates open.

Checkpoint precision: NoDb canonical Hydration and Cache Contract now documents
synthesized ESTALE read-drift classification and same-descriptor byte/version
association, with implementation pending. The integrity repair restores existing
disk-authority intent; the newly explicit error classification is reviewed and
committed before implementation. Test replacement while the descriptor is open,
as well as replacement during decode.

Checkpoint review artifacts: `nodb_hydration_correctness_checkpoint.md` and
`nodb_hydration_security_checkpoint.md`; NODB-S01/S02 are resolved by canonical
field/error clarification. Commit this checkpoint before helper/loader edits.
