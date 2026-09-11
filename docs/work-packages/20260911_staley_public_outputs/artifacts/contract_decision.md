# Direct module outputs

Base: f854cd851. Operator explicitly directs completed output files to be placed
in postfire_debris_flow/, following established patterns. This authorizes the
bounded change and its required checkpoint, plus repair of addicted-reservist.

Canonical delta: production_m1.md, Durable state and immutable artifacts and
Fixed completed-file access. Supersede hidden-only completed publication with
four ordinary top-level files using the existing browser access model. Existing
fixed-file API, NoDb concurrency, and RQ response contracts remain unchanged.

Compatibility: additive files; retained immutable accepted originals and download
API; no schema/engine fingerprint/parameter changes. Publish after accepted NoDb
commit, under the existing NoDb lock, via verified private copies and per-file
atomic replacement. Four files are not a multi-file transaction. Failure is
explicit; accepted output can be republished without another numerical run.

Boundaries: new publication helper, facade completion hook, focused filesystem
and facade tests, canonical docs. No browse/security bypass, custom UI, or
queue changes. Ordinary project browsing intentionally gains access to these
four accepted files; hidden source uploads remain hidden. No new secrets.

States: absent/empty no-op; first accepted and scientifically partial publish;
new accepted replaces; failed/unaccepted preserves prior files; existing accepted
state can be backfilled unchanged; tampered/symlink/malformed source rejects.
Validation: real files/hash equivalence, replacement, absent, tamper, symlink,
NoDb completion hook, existing live project and browser downloads. Full suite
remains on operator hold. Independent correctness and security review required.
