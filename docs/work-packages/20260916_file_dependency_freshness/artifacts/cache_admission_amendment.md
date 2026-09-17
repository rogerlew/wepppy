# Cache admission amendment checkpoint

Ancestor: `43317704f`. Initial implementation remains uncommitted and unreleased.
A correctness review demonstrated equal-size rewrites with restored mtime and
unchanged full stat keys returning an old cached hash. This refutes an explicit
initial contract assumption, so first-wave implementation acceptance is on hold.

Proposed bounded correction and rationale are in
`docs/adrs/20260917-file-digest-cache-admission.md` and the canonical freshness
contract's Timestamp-quantum cache admission amendment. Owner's audit/fix
execution authorization covers the measured cache correction; no scientific
parameter, permissions, identity or production deployment is changed.

Independent correctness and security reviews must approve this amendment before
its strategy is implemented. Commit the amendment/review disposition as an
ancestor of the eventual implementation commit. The original failing tests and
review probes remain retained, including failed intermediate runs.

Acceptance: real-clock rapid rewrite detection on overlay/repository/NFS;
fresh hashing throughout observation; fresh admission after one second;
bounded memory; no unchanged input bytes read on 100 settled warm status reads;
strict finalizer checks and ordinary valid downloads preserved. Rebuild/restart
and UI/RQ/WEPP acceptance remain required and have not happened.

Independent checkpoint reviews pass in `cache_admission_correctness_review.md`
and `cache_admission_security_review.md`. Both require observation-generation
separation across cache eviction and retained real-clock regression evidence.
No implementation approval or runtime acceptance is implied.
