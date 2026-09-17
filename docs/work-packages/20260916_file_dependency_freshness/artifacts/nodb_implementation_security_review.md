# NoDb hydration implementation security review

## Findings and verdict

**PASS for the scoped NoDb hydration implementation security review. No
unresolved scoped findings. Runtime and final package acceptance remain open.**

| ID | Severity | Evidence / disposition | Status |
| --- | --- | --- | --- |
| SEC-M1-01 | Medium, original integrity defect | Both loaders now receive text and stat from one opened descriptor and assign its mtime/size after decoding. Real decode-time replacement tests return A with A's signature and reject it as current B. | Resolved by implementation and direct regression evidence. |
| NODB-I01 | Low, test precision | The initial pytest case replaced the pathname before the helper's first fstat. The retained independent probe and revised permanent pytest case both replace inside `read()`, between production descriptor stats. The probe additionally observes real ctime change/link-count 1 to 0 with complete old bytes/version preserved. | Resolved by independent evidence and permanent regression refinement. |

This review does not approve runtime delivery or package closeout. It leaves
NoDb's existing supported cooperative writer model and separate out-of-band
preserved-time limitations unchanged.

## Metadata and security triage

- Reviewer: independent `freshness_security`, 2026-09-17 UTC.
- Reviewed ancestor: `4e000950a49ac1ae0dca85aed1c36abcda3c9de1`.
- Scope: `_read_retry.py`, `_read_retry.pyi`, disk paths in
  `NoDbBase._hydrate_instance` and `load_detached`,
  `tests/nodb/test_hydration_snapshot.py`, and related retry characterization
  updates.
- Authority: canonical NoDb persistence contract, Hydration and Cache Contract /
  Coherent disk-read versions; reviewed
  [NoDb security checkpoint](nodb_hydration_security_checkpoint.md).
- Impact remains high for the work package because hydration versions gate
  integrity and later stale-write rejection. This wave changes no authentication,
  path authority, secret, dependency, queue, subprocess or network surface.

Reviewed source SHA-256 values:

```text
_read_retry.py  1623c486e6a1ef5aaf8919ab77623ced931ad837160c78dd02fd1a586fe878fd
base.py         7231fc8367062a024c05f64a0fa7045ab81fd2f83f7a025472ee051aa85e8522
_read_retry.pyi 6cc844bc190b4129a3c53817447ec51bc47b85487f28c9168fa548c894c5b391
```

## Boundary assessment

`read_text_snapshot` opens once, fstats that descriptor, reads text and fstats
the same descriptor again. It compares device/inode/size/nanosecond mtime and
raises `OSError(ESTALE, ..., path)` on observable drift. Ctime is deliberately
excluded, as approved: unlinking an old inode during an ordinary atomic replace
does not make its complete bytes an invalid earlier generation.

Both loaders consume the returned `(text, stat_result)` pair, preserving it
through preprocessing and decode, then assign `_nodb_mtime` and `_nodb_size`
from that descriptor stat. The later independent pathname stat has been removed.
Returning older A during replacement is safe under the contract because A keeps
its own version; cache comparison and stale-write rejection remain based on the
current durable file. No old payload is relabeled with replacement B's version.

Read failure occurs before decoding, logging initialization or Redis cache
publication. The existing `_call` boundary retries only the entire open/read
transaction inside its explicit initial-read context. It does not retry a
mutation or dump. Optional ENOENT still returns None immediately; EACCES and
other nonretryable errors retain their objects and errno; synthetic ESTALE
includes the path and propagates immediately outside the context. Deadline,
backoff and diagnostics are unchanged. Existing `read_text` remains available.

The `.pyi` return type and `__all__` match the implementation. JSON serialization,
singleton identity, detached behavior, Redis fast-path validation, locks,
stale-write checks, atomic temp-file replacement, mode/umask and fsync behavior
are unchanged. The change does not make metadata an authority for arbitrary
nonparticipating in-place writers.

## Validation evidence

Independent reviewer run:

```text
wctl run-pytest tests/nodb/test_hydration_snapshot.py --maxfail=1
```

`nodb_security_focused.log`: **6 passed**, 2 warnings, 8.74 seconds. Tests use
real files and real replacement; hooks schedule the race, rather than mocking
filesystem identity. They cover both loaders, Unicode old-descriptor content,
optional/required missing input, original permission error identity, and read
drift with zero retry outside the context or one read-only retry inside it.

The independent follow-up ran:

```text
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/nodb_open_read_security_probe.py
```

`nodb_open_read_security_probe.log` records exit 0 on iteration 0 with actual
`ctime_changed=true`, descriptor link count changing from 1 to 0, and
`old_payload_and_old_version_preserved=true`. Replacement is scheduled inside
the descriptor's `read()` after the production helper's initial fstat. The
helper returns the complete earlier Unicode content with that inode's version;
the path contains the newer content. This directly closes the NODB-I01 timing
gap without production code or test edits by the reviewer.

Author logs inspected:

- `nodb_failing_baseline.log`: retained pre-fix reproduction.
- `nodb_focused_revision2.log`: **155 passed**, 8 warnings, 17.99 seconds across
  hydration snapshots, initial retry, NoDb unit/misc and boundary characterization.
- `nodb_stubtest.log`: `_read_retry` stubtest passes with no issue.
- `nodb_review_regressions.log`: **76 passed**, 8 warnings, 15.62 seconds after
  the during-read test refinement and new `hydrate`/`detached` stale-dump tests.
  The latter execute the real stale-write rejection path after decode-time
  replacement and verify replacement B's bytes are preserved. The production
  source hashes listed above were reread and remain unchanged.

These checks do not establish production NFS behavior, restarted-stack delivery
or the full repository sanity gate. The initial fixture adjustment in existing
retry tests is legitimate: cold hydration no longer has a pathname-stat stage
after reading, so disappearance must occur at its actual open boundary.

## Residual risk and final scope

The original mixed-generation payload/signature finding is closed for the two
changed disk loaders. Metadata cache/write keys, Redis mtime tolerance, filesystem
visibility and out-of-band same-metadata writers retain their prior explicit
limits; no broader guarantee is asserted. The new helper's error classification
is covered by the checkpoint rather than silently broadening retries.

Scoped security sign-off: `freshness_security`, 2026-09-17 UTC. Retain final
correctness/QA disposition. Full package validation, observability and actual
rebuilt/restarted workflows remain separate required gates. There is no risk
acceptance or authorization to bypass them in this scoped pass.
