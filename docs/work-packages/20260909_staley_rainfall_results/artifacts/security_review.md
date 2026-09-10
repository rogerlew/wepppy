# Security review: local rainfall and M1 results

## Findings and verdict

No confirmed security finding in the reviewed implementation. Unresolved high,
medium and low security findings: **0 / 0 / 0**.

**Gate: pass, including approved R02.** CLI design, NOAA design, events,
inverse results and persisted semantic validation have been reviewed. Final
sign-off follows the correctness and QA reviews: all six medium correctness
findings and QA's medium Q01 are closed. No security remediation is outstanding.
The operator approved unavailable sparse ranks; decision provenance and behavior
are recorded in [ADR-0062](../../../adrs/ADR-0062-staley-local-rainfall-results.md).

## Metadata and triage

- Reviewer: independent dedicated security-review agent.
- Date: 2026-09-09 Pacific.
- Working-tree base: `2238fc2ce55e91841c6b9795ee58081547726bdd`.
- Scope: `rainfall_io.py`, `rainfall.py`, `results.py` and the canonical
  [rainfall/results contract](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/rainfall_results.md).
- Security impact: **high** under the repository's default file/path-handling
  triage; dedicated review required. Exposure is an explicit trusted local Python
  boundary, with no public endpoint or worker integration.
- Related reviews: [correctness review](correctness_review.md) and
  [QA review](qa_review.md); security evidence does not substitute for either.

Threat assumptions follow the canonical contract's "Execution contract: local
file boundary": callers control explicit paths and expected SHA-256 values;
input files and their ancestors have trusted immutable ownership. Embedded
provenance is data, not a filesystem instruction. Output is a fresh caller-owned
directory. Public uploads, hostile concurrent filesystem writers and live
controller freshness are outside this boundary.

## Surface checks

### Valid states and user-visible errors

Direct checks preserve a valid JSON file, numeric Parquet, complete real Wallow
predictor snapshot, a controlled one-event climate snapshot, omitted NOAA CSV,
fresh output and successful event listing/detail. Malformed query arguments and
incomplete bundles fail explicitly. Existing results retain their original
manifest digest after an attempted overwrite. The correctness review records
complete-source parity plus empty/dry, missing-S, partial-F and inverse-state
coverage; package evidence also retains historical unknown-T results. QA confirms
direct-file regression closure with 62 focused cases, including complete and
missing-predictor sparse-rank guards. Its two low quality follow-ups do not
change this security verdict.

### Authentication, sessions, secrets and authorization

No route, auth/session/JWT/CSRF, credential or role changes. These local functions
do not establish run-scoped authorization; a future public caller needs its own
approved transport/access contract. No new secret handling or credential logging
was found in the reviewed files.

### Input, output and filesystem safety

`rainfall_io.py:38` rejects parent traversal, leaf/ancestor symlinks and nonregular
files before opening; files have explicit byte limits. Expected input digests
are mandatory and consumed files are rechecked (`:62`, `:74`). JSON rejects
duplicate keys, nonfinite constants and overflowing exponent literals (`:80`,
`:89`). Parquet uses a file object, bounded
metadata/dimensions/declared decoded bytes, primitive numeric climate schemas,
duplicate-column rejection and external-chunk rejection (`:116`).

Predictor reads use only four fixed `wbt` artifact names (`rainfall_io.py:147`);
source/prepared provenance paths are never reopened. Result loading similarly
uses fixed table names, expected manifest/table hashes, exact Arrow schemas and
bounded row counts (`results.py:122`). Stronger validators check predictor
geometry, K/F/S provenance, WBT support, result identities/units, complete unique
combinations and scalar consistency (`rainfall_io.py:167`, `:219`;
`results.py:206`, `:226`). They reopen no additional source or provenance paths.
No SQL, eval, pickle or shell execution is
introduced. Queries use fixed filters and sort allowlists with bounded pages
and structured event IDs (`results.py:162`, `:195`).

Outputs use fresh mode-0700 directory creation and exclusive file opens
(`results.py:84`; `rainfall_io.py:108`). No approved run-root confinement is
claimed: explicit caller-owned output paths are the accepted local interface.
Incomplete files remain for diagnosis; table readback and source rechecks precede
manifest publication. Failed or hash-mismatched bundles are not returned as
validated query catalogs.

### Queue, subprocess, agent tooling, network and supply chain

Supported CLI ranking (`rainfall.py:176`) reuses the existing shared rank helper
and parsed/pinned source data. Full recurrence-context CSV parity adds no
external read or execution boundary. Approved sparse unsupported ranks produce
unavailable rows with retained rank/count and null rainfall/probability.
Reopening requires every CLI design row retaining rainfall to have a supported
rank, including missing-predictor rows (`results.py:301`). The insufficient-sample
reason is limited to CLI design rows with positive count and unsupported rank.
This closes the clamped-result consistency gap without adding file access.

No queue edges, worker/subprocess calls, agent/MCP permissions, downloads,
external readers, routes, CI/deploy changes or dependency additions occur in
the reviewed runtime scope. Existing tabular dependencies remain in use.
RQ graph and frontend gates are not applicable to this security review.

### Data integrity, concurrency, logging and recovery

No NoDb/Redis mutation or existing Climate/predictor artifact rewrite is added.
Pinned source digests are rechecked before successful publication; the reader
rechecks manifest/table files after loading. Real-file mutation checks fail
explicitly. Native filesystem/scalar errors remain visible; no broad exception
swallowing was found. Fresh-path retry and retained incomplete files are the
documented recovery mechanism. Permissions and overwrite protection were
checked directly, without mocks.

## Validation evidence

Run from repository root:

```bash
wctl run-python docs/work-packages/20260909_staley_rainfall_results/artifacts/security_probe.py
```

Result: **29 direct checks passed, exit 0**, using container PyArrow 23.0.1.
The [reproduction script](security_probe.py) uses temporary owned files and the
existing complete Wallow predictor bundle; no production file is changed.

Checks cover valid regular JSON/numeric Parquet; leaf and parent symlinks;
parent traversal; FIFO rejection before open; byte and row limits; missing/wrong
digests; source mutation; duplicate/nonfinite JSON; nested/string/duplicate
Parquet columns; a real external-chunk metadata file; private output and valid
round-trip queries; pagination bounds; sort injection; malformed event ID;
existing-output preservation; output-parent symlink; incomplete output;
manifest hash mismatch; result-table mutation; overflow JSON exponents;
manifest-controlled table traversal; and nonopening of nonexistent paths
embedded in result/predictor provenance.

The correctness review independently records 18 semantic boundary probes and
12 genuine CLI design combinations matching full-context rounded CSV evidence.
It also verifies the approved sparse-result round trip with unchanged Climate
CSV clamping evidence. Its six medium findings are closed. Security inspected
the final retained-rainfall rank guard and matching rehashed regressions and
found no new path, decoder, execution or egress surface.
Final runtime SHA-256 values below match the subsequent completed QA review.

Reviewed runtime SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `rainfall_io.py` | `a08f89fc746c631dcc1ae033c42e4f7f86bdaf4eadaa90adc7804a442642e1bd` |
| `rainfall.py` | `fd1da7a6ec7ce21268f7089b90d083ebfade9f66f49937396a59230531efa3da` |
| `results.py` | `e8ab818669c41b039be8ea0256bf32e42dc5d263186e4319fb877b1e5b6f985a` |

## Residual risk and sign-off

The trusted-local assumptions are material: pathname checks plus separate
hash/read/recheck operations do not defeat a malicious concurrent writer who
can swap and restore files. Metadata limits do not sandbox native Parquet
decoders or bound all Python/Pandas allocation overhead. Expected hashes prove
snapshot identity, not scientific truth, caller authority or live freshness.
Full predictor provenance, including local paths, remains local output metadata;
future publication needs a separate disclosure review. These are explicit scope
limitations, not accepted unresolved findings.

Security reviewer sign-off: **pass including approved R02**, after final
correctness/QA findings closure, final-runtime digest verification and a passing
29-check direct security rerun. Full package delivery remains the executor's
responsibility; no security approval remains pending.
No owner risk acceptance was requested or recorded.
