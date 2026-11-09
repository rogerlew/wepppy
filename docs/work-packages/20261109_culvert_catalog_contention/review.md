# Independent correctness and security review

Reviewer: `culvert_review`, 2026-11-09. Scope: serializer integration in
`catalog_refresh.py`, pilot receipt wrapper, culvert traceback logging and new
real-process regression coverage.

No must-fix code defect found. Exclusive owner fencing, nonblocking genuine
lifecycle conflict handling, reentrancy and strict missing-directory refusal
remain intact. Existing restore/namespace tests cover lifecycle-owner reentry;
new process tests cover changed catalog critical sections. No authorization or
isolation weakening identified.

Required follow-through: execute pilot/worker peer suites with disposable Redis,
complete parallel replay and artifact checks, and update the plan/tracker.
Documentation was corrected to distinguish candidate collection outside locks
from final inventory/schema revalidation inside publication ownership.

Residual risk: real parallel integration behavior remains subject to replay
acceptance. This review does not authorize production deployment or establish
cross-host filesystem parity.

## Follow-up review: HTTP compatibility and stateless WBT

The broad suite invalidated the initial review's completeness: catalog HTTP
callers historically wait through lifecycle contention. The revised metadata
guard retries acquisition only, releases the serializer between attempts and
never replays a caller body. Six HTTP contention tests and additional real-process
reentrancy/deleted-tree/body-error tests pass. Reviewer found no remaining blocker.

WBT review expanded coverage to the pip binding and bundled plugin subprocesses.
All three bindings keep invocation options/cwd local; plugins receive effective
configuration. Initial atomic-save review found ownership/group and settings
symlink regressions, then a too-permissive temporary. All were corrected before
forest installation. The final temporary starts mode0600; absent-file default
permissions come from an empty probe. Existing owner/group, mode, Linux ACLs,
xattrs and symlink targets are preserved or publication fails explicitly.

Independent executable probes on SHA-256
`28208e075a51f37d254a51b2a9f27c0ef7e5f273344c8665a0749b4714766777`
confirmed UID/GID1000:4, mode0640, symlink target, named POSIX ACL and user xattr
preservation; new-file umask027 yields0640; no temporary/probe residue. FFI buffer
bounds reviewed, including zero-length xattr growth. No remaining blocking
finding for forest/Linux installation. Windows/macOS metadata parity and external
prebuilt plugins are not established by these checks. Full fresh parallel batch
acceptance remains required.


## Live regression review

Reviewer identified that single-worker execution could pass the initial test.
Added completed-child timestamp overlap assertion, excluding finalizer; require
peak >= 2. Both fresh replays have peak4; a serial/touching-interval probe fails
as required. Second live pytest passed end-to-end; the new overlap assertion
was run separately on its completed jobs because the running test had already
loaded its module. No other blocking acceptance finding.
