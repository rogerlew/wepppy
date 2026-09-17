# CLI same-call directory descriptor reuse security review

Disposition: **PASS for this bounded optimization**. No unresolved medium/high
finding in the changed boundary. This supplements the CLI implementation review;
it does not approve performance, full runtime acceptance, or package closeout.

Reviewed `rainfall_io._local_parent`, `_verify_parent`, `open_local` and
`production._cli_lineage_current`/`cached_digest`. One request can hold an
`O_RDONLY | O_DIRECTORY | O_NOFOLLOW` parent descriptor for both CLI leaves.
There is no descriptor cache or reuse across requests. The helper continues to
reject selected ancestor/leaf symlinks, opens each leaf for actual read access,
and binds the held parent to its visible pathname. The surrounding source checks
retain leaf descriptor/path versions and strict signature checks. Different
parents still follow the ordinary traversal. `ESTALE` becomes `changed_source`.

Independent retained command:

```text
wctl run-pytest docs/work-packages/20260916_file_dependency_freshness/artifacts/cli_lineage_parent_reuse_security_probe.py -q
```

Result: **9 passed in 17.65s**, full output in the adjacent `.log`.

- After reading a real produced Parquet footer, rename the selected climate
  directory and replace it with a different directory whose leaves are hardlinks
  to the original CLI/Parquet. This preserves leaf byte/inode observations while
  changing parent identity. Both content modes reject with `changed_source`.
- Replace a parent after default `open_local` opens its leaf. The parent mismatch
  raises `ESTALE`; the leaf descriptor is closed (`EBADF` on inspection).
- Real UID 1000 access checks reject unreadable directories at modes 0111/0000.
  This confirms the optimization did not substitute `O_PATH` and bypass the
  previous directory-read permission requirement.
- Ancestor, immediate-parent and leaf symlinks remain rejected. A leaf changed
  to mode 0000 is denied when using an already held parent descriptor.

The checks establish observed point-in-time association, not isolation from
arbitrary concurrent writers after the final check. No production/tests were
edited by this reviewer; only disposable probes and review artifacts were added.

## Proposed performance-budget correction

Security disposition: a documented correction from the prototype's 5 ms settled
/ 40 ms cold budget to **10 ms / 50 ms**, supported by representative actual
predicate measurements, is preferable to weakening directory read authority or
adding a cache of open descriptors across requests. Preserve the original misses
and profiling evidence. The parent must amend the authoritative contract and
decision rationale before release, identify workload/measurement conditions, and
retain QA's final acceptance. This is a security tradeoff assessment, not a claim
that the proposed budgets or full runtime gates have already passed.

Reviewed source SHA-256:

```text
rainfall_io.py f61f0c76caee6ba10583ce19a6628f48c6e0efca6b229f79f172450c3ae39898
production.py 8c66a2f8c29b8da5e75bc27bfa0ed494fe4abb43cb7913a8ad5f394cf0ac38c3
```
