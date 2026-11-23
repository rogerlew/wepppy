# Project RQ read-only transition refactor

The maintenance target is the nested catalog and browse-manifest logic in
`set_run_readonly_rq`. Extract those operations as private functions. The RQ
entry point continues to own policy, locking, marker changes, rollback, and
terminal messages. The earlier subcatchment extraction is a closed package.

The complexity budget allows private functions and regression coverage within
the existing worker and test module. Security impact is low because the
existing policy and catalog lifecycle guard govern both operations. A dedicated
security review is unnecessary. Acceptance requires worker-level tests covering
parent and child runs, catalog readback, manifest verification and failure
recovery. Integration is local by operator request.
