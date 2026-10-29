# Correctness and user-experience review — project developer mode

Status: runtime review scaffold; not an implementation approval. Prepared 2026-10-29 UTC against base `cebb4b4283e408fd270126811f4dbbd1a8dfd8e2`.

## User outcome and state matrix

Dev activates enable-only Ron mode (archive/fork recovery uses incoming mode); ordinary authorized callers use elevated anisotropy; clones retain policy. The checkpoint's state/error matrix and DM-01 define absent, blank, populated, legacy and malformed states separately from input/role combinations. Validate actual UI reachability, failed/lost requests, idempotence, concurrency, readonly, cloning and archived/working/failed/completed states.

## Evidence and final review gate

Use `docs/prompt_templates/correctness_review_template.md` for the final review. Require direct locked persistence, request and copy/restore tests, actual native writer readback, current-runtime model execution/output or retained numerical failure, and normal browser/download/archive evidence. Compare original soils and unrelated prepared fields. Security controls must preserve valid states. No runtime evidence is present yet; gate **hold**. Highest claim: documented design. Reviewer sign-off: pending; implementation and deployment are not established by contract review.
