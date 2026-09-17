# Controller bundle header correctness checkpoint

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC. Reviewed
`bundle_header_contract_decision.md`, the canonical freshness contract's
Controller bundle header identity section, `utils/assets.py`, its context
processor caller, controller README, stale-client comparison and existing tests.
Starting implementation revision: `4e000950a`, with the earlier reviewed waves
still in the working tree. No implementation edits made by this reviewer.

**Verdict: PASS for this bounded contract checkpoint. No blocking finding.**
The amendment ratifies the existing generated-header identity and removes the
demonstrably incorrect assumption that equal pathname, size and mtime mean an
unchanged header. The real-call baseline in `m1_correctness_probe.json` already
shows an old build ID after a same-size/restored-time update. Reading the existing
small header again is the smallest sufficient repair; the scientific digest
cache and its admission policy are unnecessary here.

## Behavior and compatibility

`resolve_controllers_gl_build_id` retains its current 80-line scan, UTF-8 decoding
with replacement, `Build date:` substring matching and whitespace stripping.
The first matching but empty value still ends the search with `None`; do not
silently introduce stricter date parsing or a different later-match rule.
Missing, empty, unreadable and headerless files remain unknown. A later access
denial must not be hidden by an earlier successful lookup.

The context processor continues to prefer the configured static sync directory,
then the application static folder. It captures one expected ID per context
invocation and uses that same value for the rendered dataset and controller
asset `cg` query parameter. Keep this per-request agreement. The next context
invocation must observe a changed header without restarting the Python process.
Unknown identity continues to suppress the stale banner and omit `cg` as today;
no schema, persisted identity or legacy migration is introduced.

A descriptor opened before atomic replacement may read the complete earlier
header. The next call opens the current pathname. This is appropriate for the
stated point-in-time contract and does not require rejecting a complete old
generation. Touch, chmod that preserves readability, hard links and identical
replacement leave the returned header value unchanged. Arbitrary concurrent
in-place publication is not newly guaranteed to produce an atomic bundle.

The existing 80-line limit is a line limit, not a byte limit. Generated headers
place the value near the beginning; a malformed giant line can still cost more.
That existing parser behavior is outside this repair and does not justify a
new parser or file-authority policy. Served-file alignment, symlink handling,
client comparison, authentication and authorization remain unchanged.

## Implementation acceptance still required

- Exercise the real resolver with equal-size changed headers and restored mtime,
  both by in-place rewrite and atomic replacement; no cache reset or sleep.
- Cover missing, empty, headerless, invalid UTF-8, whitespace and the 80-line
  boundary. Verify readable metadata churn preserves the ID and loss of read
  access yields unknown after an earlier successful lookup.
- Verify two context invocations expose the new expected ID and matching `cg`
  after replacement while retaining candidate priority and unknown behavior.
- Retain the planned 1,000-call benchmark on the actual generated bundle and
  representative mount, including bundle/header identity and measured mean.
  The proposed mean below 1 ms is an acceptance budget, not yet measured proof.
- Preserve existing template/stale-client regression coverage and complete the
  restarted Flask rendered-ID check against the actually served bundle.

No implementation or runtime acceptance is claimed here. The independent
security review and standalone checkpoint ancestor commit must precede edits;
the broader package's remaining consumers and final gates remain open.
