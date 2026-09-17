# Controller bundle header implementation QA

Reviewer: independent `freshness_qa`, 2026-09-17 UTC. Accepted checkpoint:
`984023c18`. Scope: `wepppy/weppcloud/utils/assets.py`, its resolver and Flask
context tests, affected README, and retained benchmark. No code edits or new
test executions by this reviewer.

## Disposition

**PASS for scoped maintainability and test quality. No blocking QA findings.**
The 15-line deletion removes the demonstrated invalid cache assumption and
reduces state and branches without adding another identity mechanism. Existing
parser behavior remains directly visible and unchanged. The reviewed checkpoint
establishes correctness/security intent; final implementation reviews and
restarted runtime acceptance remain separate gates.

## Implementation and tests

`resolve_controllers_gl_build_id` now opens the configured file for every
lookup. The 80-line scan, UTF-8 replacement decoding, first matching header,
empty-value stop, and `OSError` to unknown behavior are unchanged. No new
dependency, persistent state, fallback, broad exception handler, or parser policy
is introduced. Removing the global result dictionary also removes stale
cross-request state and its unbounded path-key accumulation.

The unchanged context processor captures one ID per invocation. The new Flask
test verifies that an already-created context keeps its matching expected ID
and `cg` URL value after a file change, while the next request obtains the new
ID. This protects both freshness and internal request consistency.

The resolver regression performs real equal-size header rewrites with restored
mtime, both in place and through `os.replace`, in the same process without
cache resets or sleeps. It then deletes the file and verifies unknown identity.
Compatibility cases cover empty/headerless input, a first empty matching value,
the rejected 81st-line header, invalid UTF-8 and whitespace. An injected read
denial after a prior successful lookup checks that earlier success cannot bypass
the open/error path. That injection demonstrates error behavior, not actual
UID/GID permission enforcement.

`bundle_header_tests.log` records **12 passed** across the resolver and Flask
context modules. The tests target observable behavior and use real files at the
original failure boundary. Existing asset-version, unrelated-asset URL and
unknown-ID tests remain in the run.

## Performance and residual limits

`bundle_header_benchmark.json` records 1,000 calls against the actual 2,195,371-byte
generated bundle at `/workdir/wepppy/wepppy/weppcloud/static/js/controllers-gl.js`.
Its observed ID is `2026-09-16T23:08:27Z`; mean lookup time is **42.68 microseconds**,
below the accepted 1 ms budget. The retained script asserts a nonempty final ID
and the mean budget. This is repeated local lookup evidence, not cold-storage,
concurrent-load, or all-mount performance evidence.

No implementation refactor is recommended. Non-blocking residual coverage:
readable touch/chmod/link churn, identical replacement, and replacement between
open and read are not individually exercised by the new bundle tests. Source
inspection supports their unchanged parser/open behavior; retain representative
runtime evidence where the package's operation matrix requires it. A positive
80th-line parser case would complement the existing 81st-line rejection if that
unchanged parser is edited later.

The established line limit does not bound arbitrary line byte length. Header
identity also cannot distinguish different bundle bytes carrying the same date.
Both are existing limits documented by the checkpoint, not reasons to expand
this fix into parser hardening or full-bundle hashing.

Restarted Flask rendering still must agree with the actually served bundle
under the deployed static-directory configuration. Broad sanity, remaining
consumer inventory disposition, and full-package runtime/archive acceptance
are not closed by this QA pass or the local benchmark.
