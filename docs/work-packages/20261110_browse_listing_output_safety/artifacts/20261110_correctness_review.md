# Correctness and user-experience review - Browse listing output safety

## Metadata

- **Package**: `docs/work-packages/20261110_browse_listing_output_safety/`
- **Reviewer**: unassigned; must be independent of implementation author
- **Date**: pending
- **Implementation revision**: pending
- **Gate status**: fail until implementation evidence is reviewed

## User Goal

An authorized user can browse files with their actual names and use all existing
actions without any filename or symlink display value becoming executable HTML
or changing the destination of a link.

## State Matrix

| State | Expected user-visible result | Required evidence |
| --- | --- | --- |
| Empty directory | Header, breadcrumb, and empty-state text render normally | Focused existing control |
| Ordinary ASCII entries | Labels and all applicable actions remain unchanged | Route response and link resolution |
| Unicode/punctuation entries | Original label is readable; encoded link opens the same entry | Real temporary entry and GET |
| HTML-sensitive filename | Characters appear as text; no new element/attribute exists | Response/HTML parser assertion |
| HTML-sensitive directory | Listing and nested breadcrumb remain inert and navigable | Two route responses |
| Symlink with hostile display target | Target appears as text only; current traversal policy is unchanged | Real symlink where supported |
| Parquet/action-bearing file | Download, CSV, D-Tale, and schema links retain filters and target | Focused action-link assertions |
| Diff-enabled file | Diff query state and encoded filename both survive | Focused diff control |
| Missing path | Existing 404 remains safe and understandable | Only if not-found code is patched |
| Manifest/virtual entry | Shared renderer applies the same encoding | Renderer-level evidence; no archive restoration |

## Compatibility Risks to Review

- Double encoding can make an existing file unreachable, especially names with
  `%`, spaces, `#`, `?`, or Unicode.
- Escaping before width calculation can damage alignment; calculate presentation
  width from original display text and escape only at emission.
- Using filesystem joins for URL assembly can create platform or separator
  semantics; join trusted URL prefixes with encoded segments.
- Rebuilding query strings incorrectly can lose `diff`, `pqf`, sort, or filter
  state.
- Removing all safe markup without replacing intentional anchors can expose raw
  HTML text and make the listing unusable.
- A filename allowlist would hide legitimate artifacts and violate the browse
  filesystem contract.

## Required Direct Evidence

- [ ] Red tests fail on the pre-fix renderer for the intended reason.
- [ ] Green tests create actual temporary names and symlinks; they do not mock
      the output string.
- [ ] Ordinary and Unicode links return the intended file or directory.
- [ ] Hostile corpus yields no injected tags or attributes.
- [ ] Every changed action keeps its route prefix and query values.
- [ ] Existing authorization and containment outcomes are unchanged by review.
- [ ] Exact focused commands, counts, revision, and limitations are retained.
- [ ] No full-suite or production claim is made.

## Verdict

Pending. Closure requires all valid states above to pass and no unresolved
High/Medium correctness or user-experience finding.

## M0 independent review

Reviewer `/root/correctness` (`reviewer`), 2026-11-11 UTC, base
`c040d51d09530dee7f1562c467b98d74c8d6c5a4` plus contract amendment: approved,
no blocking findings. Implementation cautions accepted: `.htm` lacks default
autoescaping, missing-path breadcrumbs need the planned repair, and action
coverage must include raster, annotated and diff alongside Parquet.
