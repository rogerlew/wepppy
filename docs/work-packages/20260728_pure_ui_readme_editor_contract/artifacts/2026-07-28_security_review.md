# SURF-09 Security Review

**Date**: 2026-07-28
**Reviewer**: independent Codex security reviewer
**Final disposition**: Pass

## Scope

Reviewed authenticated README viewer/editor routes, owner and readonly
authority, active-root path confinement, Redis lock and revision coordination,
request validation, Markdown/Jinja rendering, browser response handling, and
the focused regressions.

## Findings and Resolution

- Redis absence and errors previously permitted unsafe coordination behavior.
  Editor entry, state reads, and mutations now fail closed.
- Route aliases could split lock identity. Lock and client state now use a
  digest of the resolved active root, with composite-run ownership resolved to
  the parent.
- Concurrent and late saves could overwrite newer text. A scoped mutation
  guard, exact lock ownership, and monotonic client revisions now precede the
  atomic write.
- UUID, JSON shape, request size, source size, and rendered size required
  explicit bounds. The routes now validate all of them before mutation.
- Streaming output alone did not prevent Jinja expressions from allocating a
  large intermediate value. The renderer now accepts only literal Markdown
  plus variable, attribute, and constant-key interpolation; filters, calls,
  control structures, and operators are rejected before evaluation.
- Viewer/raw reads no longer create a file, and the default template passes
  route-controlled values as variables rather than recursively evaluating
  configuration text.

Regressions cover multiplication, percent formatting, `center`, `range` plus
`join`, oversized request envelopes, recursive configuration input, symlink
escape, stale locks and revisions, alias identity, Redis failure, and
owner/readonly enforcement.

## Gate

No unresolved high- or medium-severity findings remain.
