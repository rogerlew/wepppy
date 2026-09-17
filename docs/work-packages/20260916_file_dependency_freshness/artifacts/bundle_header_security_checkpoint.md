# Controller bundle header security checkpoint

## Findings and disposition

**PASS for the proposed C10 checkpoint; no open scoped findings.** This is a
contract review, not implementation, performance or runtime approval. No
production code or tests were changed by the reviewer.

Reviewed on 2026-09-17 UTC at `4e000950a49ac1ae0dca85aed1c36abcda3c9de1`, with
the proposed `bundle_header_contract_decision.md` and canonical
`docs/schemas/file-dependency-freshness-contract.md`, **Controller bundle header
identity**, in the working tree. The package's broader file-handling security
gate remains applicable; this bounded change removes a stale result cache for
an existing trusted application asset.

## Concrete boundary and noninterference

`wepppy/weppcloud/utils/assets.py:resolve_controllers_gl_build_id` currently
reuses the extracted header value by pathname, mtime and size. The retained
`m1_correctness_probe.py` writes two equal-length dates to a real file and
restores its mtime; `m1_correctness_probe.json` records
`assets.stale_build_id_returned=true`. This is a demonstrated false-current
result, with no adversarial writer or fabricated stat required.

The proposed removal preserves the same `Path.open` text read, UTF-8 replacement
decoding, first `Build date:` handling, whitespace stripping and 80-line scan.
No full-file hashing or additional identity store is needed to obtain this
existing UI identity. Missing, empty, unreadable and headerless assets still
produce `None`; a previous success cannot conceal a later read denial once the
cache is removed. Removing the stat/cache path does not remove a containment
check: that path currently establishes only cache identity.

`_context_processors.py:versioned_static_processor` supplies paths from
`STATIC_ASSET_SYNC_DIR` and `app.static_folder`, not request-controlled input.
Its existing candidate order and fallback, `cg` query parameter, and expected
ID injection remain unchanged. The header producer
`controllers_js/templates/controllers.js.j2` supplies the same date to the
comment and `window.__weppControllersGlBuildId`. `templates/base_pure.htm`
retains template escaping, and `static/js/controllers_gl_stale_check.js`
retains its unknown-expected-ID early return and fixed banner text. There is
no new auth, session, CSRF, network, subprocess or run-data mutation boundary.

## Valid and legacy states

| State | Required preserved behavior |
| --- | --- |
| Readable generated header | Return its current parsed date on every lookup |
| Same-size/restored-mtime rewrite or replacement | Next lookup returns the new header; metadata cannot reuse the old value |
| Touch, chmod, hard link or identical replacement | Same parsed date when readable; no new rejection policy |
| Missing, unreadable, empty, headerless or empty date | Existing `None`; no banner solely from an unknown expected ID |
| Unusual whitespace or invalid UTF-8 | Existing parser/decoding behavior; no stricter format introduced |
| Atomic replacement during an open read | Complete old or new header allowed; next call opens the current path |

There is no persisted schema, migration or legacy cache to upgrade. An older
generated bundle remains readable under the same parser. Rollback restores the
previous metadata-cache defect but cannot corrupt a persisted record. Atomic
replacement allowance is appropriate for this point-in-time observation; it
does not claim isolation against arbitrary in-place mutation of the opened
inode. The 80-line limit remains a line-count limit, not a new byte-count bound,
on the existing trusted generated asset.

## Required implementation evidence

Retain real same-size/restored-mtime rewrite and replacement regression tests,
the unknown/error cases, and the stated 1,000-lookup benchmark on the actual
bundle. A same-process second lookup must prove the fix without restarting or
clearing a cache. Preserve the first empty-date and scan-limit behavior when
exercising unusual headers. The planned mean below 1 ms is a performance gate;
it has not been measured in this checkpoint review.

Final restarted Flask rendering must still demonstrate alignment between the
expected ID and the asset actually served. Header freshness cannot prove that
two different bundles with the same generated date have different identity,
nor repair a misaligned static mount; both are unchanged limits of the owner
contract. No risk acceptance or package closeout is implied by this pass.
