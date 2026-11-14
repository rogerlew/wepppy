# Independent Rust CLI QA Review

Date: 2026-11-14

Reviewer: independent `qa_reviewer` agent

Commit: `fe5ac7c1c`

Verdict: **FAIL / HOLD**. Critical 0; High 0; Medium 3; Low 0.

## Findings

| ID | Severity | Finding | Required action |
|---|---|---|---|
| IQA-01 | Medium | The qualified image is not provenance-identical to `fe5ac7c1c`: its sidecar says `19c0dc107-worktree`, and its `Cargo.toml` digest differs from the committed file. | Rebuild from the committed tree with the exact revision, rescan, and requalify. |
| IQA-02 | Medium | Timeout/cancellation tests use a fake process or replace the converter; they do not prove cancellation of the actual blocking parser or real descendants. | Retain real subprocess cancellation, descendant-kill, concurrent-health, and cleanup evidence. |
| IQA-03 | Medium | Required compatibility/resource coverage is incomplete: multipoint and M variants, multipart lines/polygons, deleted/logical/LDID DBF states, all MultiPatch families, malformed offsets/parts, panic/abort, and reproducible CPU/address-space/core/descendant probes are absent. The ExecPlan also names a nonexistent `test_rust_parser_semantics.py`. | Complete or explicitly disposition the matrix and correct the ExecPlan command. |

## Checks that passed

- 195 affected tests passed with 2 warnings.
- Rust formatting, 5 unit tests, and clippy passed.
- Exact-image readiness, GeoJSON and GeoParquet semantic readback, scratch
  cleanup, Fiona/GDAL absence, and SBOM hashes passed.

The exact image evidence remains useful, but it cannot approve a commit with a
different recorded source identity.
