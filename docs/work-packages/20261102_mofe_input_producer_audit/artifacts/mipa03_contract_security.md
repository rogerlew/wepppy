# MIPA-03 independent contract and security review

Reviewer: `mipa03_contract_security`, 2026-11-03 UTC. Pre-implementation
checkpoint review; this is not implementation, release, or deployment approval.

## Findings

| ID | Severity | Surface and concrete evidence | Required disposition | Status |
| --- | --- | --- | --- | --- |
| SEC-MIPA03-01 | Medium | New native cover reader: the proposed contract requires row counts and finite values, but does not explicitly rule out Fortran list-directed null fields, slash termination, or cross-record value completion. A compiled system-gfortran probe reads `1,,3` and `1 /` into three zero-initialized reals with `iostat=0`, leaving finite zeros. Reference `readrap.for:104–109` uses unrestricted list-directed reads. | Require exactly the expected numeric tokens on each physical row; reject null, slash/partial, missing and surplus fields before publishing state. Check dimension/calendar arithmetic and allocation failures explicitly without inventing scientific caps. Test these direct compiled-reader cases. | Open at initial review |
| SEC-MIPA03-02 | Medium | Changed flag/date publication and retirement: proposed text promises visible attempt records but names no concrete retention path or linked-file semantics. Current `rap_ts.py:361,430,433` and `wepp.py:1742` use truncating writes; a linked destination can modify another source inode. `pmetpara.py:22–46` is the established regular-file/replace precedent. | Name run-relative retired/attempt paths and retained bytes. Preserve absent state as no-op; do not follow symlink destinations or truncate hardlinked originals. Use bounded rename/replacement with explicit failures; retain direct linked-file, failure and archive/restore evidence. | Open at initial review |

These are clarifications of newly changed parsing and file lifecycle boundaries,
not requests to retune reference physics, expand upload admission, or redesign
existing project authorization. The parent received both findings before any
implementation approval from this reviewer.

## Scope and authority

Reviewed WEPPpy starting revision `ea5d4cdbd`, native selected revision
`4f0728984`, and the proposed uncommitted specialized contracts in both
repositories; ADR-0134; MOFE identity/coefficient amendments; and
`20261103_specialized_consumer_decision.md`. The active handoff and operator's
“preserve reference. that is anurag's domain” provide authority for the bounded
specialized numerical port. The authority excludes deployment, defaults,
Windows, expanded uploads, installed Rust replacement and bulk regeneration.

The source/binary reference is explicitly bound, and the historical compiler
limitation is disclosed. An isolated specialized growth routine is compatible
with ordinary-mode noninterference; wholesale divergent model replacement is
not. Preserved root-state sharing and canopy/fire quirks are disclosed scientific
compatibility choices. Security review does not independently certify their
physical validity or reinterpret the operator's decision.

## Security triage and valid-state obligations

Security impact is **high**, requiring a dedicated final security artifact after
correctness and QA. Added native parsing consumes run-local project data and
allocates cover state; changed producer lifecycle writes, retires and archives
activation files. These change input and filesystem attack surfaces even though
they add no network, route, credentials, authentication, queue or privilege.

The proposed mode matrix correctly separates ordinary absent optional state,
empty presence flags, populated specialized data, missing fire date, malformed
activated inputs, single-event exclusion and routed watershed passes. In
particular, no-fire zero year/day is retained as historical reference behavior;
security must not insert a fire-flag predicate that changes it. Reinitialization
per hillslope must prevent stale cover/date allocation state. Exact year and OFE
validation must preserve integer/string producer keys and supported fallback.

The derived cover path must be a run-directory basename from the current soil
basename. Parent-directory digits cannot choose another hill. File parsing must
not introduce a shell, path supplied from cover contents, or uncontrolled output
path. Existing service identity, project access checks and canonical archive
boundaries remain applicable.

## Evidence and remaining gates

Read actual producer code, the bound reference `readrap.for`, native calendar
count sites, and the established PMET replacement helper. A fresh isolated
Fortran probe at `/tmp/mipa03-security-reader-Ggjwwx` compiled with system
`/usr/bin/gfortran -fcheck=all` produced:

```text
null  iostat=0  values=1,0,3
slash iostat=0  values=1,0,0
```

This demonstrates why success plus finite values is not exact token consumption.
It is a parser characterization, not an executed exploit against a future reader.
No production files were edited by this review. No implementation tests, archive
replays or final binaries exist for this checkpoint yet; they cannot be marked
passed. Required follow-up includes real valid/hostile writer/reader boundaries,
retained failed attempts, normal browser/download and canonical archive/restore,
exact final-pair provenance, output neutrality and service-identity workflow.

## Initial verdict

**FAIL pending contract clarification:** zero high findings, two medium findings.
After concrete amendments, this reviewer must verify closure before the standalone
ancestor checkpoint. A later PASS would approve only the contract and regression
obligations, not implementation or release. No risk acceptance is requested.

## Amendment closure and final contract verdict

The parent amended both mirrored contracts with the identical "Parser and
publication boundary details" section. Independent reread and `cmp` verify
parity. Both files have SHA256
`f80f06940daaf8ea075cf97b8e636a50c8c81b93aca9b5f3eaa7d961be295452`.

- **SEC-MIPA03-01 resolved at contract level:** exact physical whitespace rows,
  exact numeric token counts, null/slash/repeat/partial/cross-record rejection,
  a stated lexical token bound, checked size/calendar arithmetic and checked
  allocation failure are now normative. The bound constrains parser storage,
  not scientific values; required scientific arithmetic remains unchanged.
- **SEC-MIPA03-02 resolved at contract level:** regular-or-absent destinations,
  rejected symlinks, no hardlink truncation, fresh visible
  `wepp/runs/revegetation-input-<unique>/<original-basename>` retirement,
  exclusive temporary writes and atomic replacement are now normative.
  Unchanged and absent optional states remain no-ops; failure evidence and
  archive/restore remain mandatory. History traversal cannot follow symlinks.

**PASS for the pre-implementation contract checkpoint.** No unresolved high or
medium contract finding remains. This approves the proposed boundaries and
regression obligations, not any unimplemented reader/writer or release. Record
this review in both standalone ancestor checkpoints before production edits.
The dedicated final security review remains required after implementation,
correctness and QA; it must verify actual parser, linked-file, failure, archive,
service-identity and exact-artifact evidence. No deployment is authorized here.
