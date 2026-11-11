# Failure-class matrix - Browse output encoding

**Status**: Initial source inventory; update during implementation  
**Date**: 2026-11-11 UTC

## Failure Class

The shared failure is insertion of filesystem- or request-derived strings into
trusted HTML without output-context encoding. The matrix distinguishes confirmed
consumers from reviewed non-consumers so implementation stays complete but
bounded.

| Consumer | Untrusted value/context | Source evidence | Initial disposition |
| --- | --- | --- | --- |
| Directory row | Directory name in label and `href` | `listing.py:857-869` | Confirmed; escape label and encode segment |
| File row | Filename in label and primary `href` | `listing.py:870-947` | Confirmed; escape label and encode segment |
| Download action | Filename in URL attribute | `listing.py:881-892` | Confirmed; encode segment and preserve query |
| Raster/CSV action | Filename in URL attribute | `listing.py:893-903` | Confirmed; encode segment and preserve query |
| Annotated action | Filename in URL attribute | `listing.py:904-909` | Confirmed; encode segment |
| D-Tale action | Filename in URL attribute | `listing.py:910-926` | Confirmed; encode segment and preserve query |
| Schema action/data attribute | Filename in two URL attributes | `listing.py:927-934` | Confirmed; encode and attribute-escape both |
| Diff action | Filename in URL attribute | `listing.py:936-943` | Confirmed; encode segment and preserve query |
| Symlink suffix | Target in HTML text | `listing.py:860,872,946` | Confirmed; escape as text, never make it a target URL |
| Directory breadcrumbs | Stored path part in text and `href` | `flow.py:420-457` | Confirmed same failure class; repair |
| Trusted listing handoff | Assembled HTML marked safe | `flow.py:580-589` and `directory.htm` | Confirmed trust amplifier; narrow or replace |
| Not-found breadcrumbs | Request path part in trusted HTML | `browse.py:783-834` | Confirmed F3-S4; raw labels, URL and diff query; retain focused red test and repair |
| Sort links | Request path plus encoded query | `listing.py:815-832` | Review after segment fix; preserve existing controls |
| Pagination | Query values encoded by `urlencode` | `flow.py:490-502` | Not confirmed; unchanged unless red evidence exists |
| Filter input | Attribute value escaped | `flow.py:453-455` | Existing control; retain |
| Copy-path attribute | Absolute path attribute-escaped | `flow.py:438-452` | Existing control; retain and regression-check changed helper |
| Manifest-backed entries | Same tuple renderer as physical scan | `listing.py:784-798` | Covered by renderer even though cache use is disabled |
| Virtual NoDir entries | Same `page_entries_override` renderer | `flow.py:71-104`, `listing.py:784-787` | Covered by renderer; no archive behavior change |
| Files JSON API | JSON serializer output | `tests/microservices/test_files_routes.py` | Not HTML consumer; source review only unless changed |
| File preview body | File contents/parser output | Browse preview dispatch | Different boundary; out of F3 scope |

## Required Corpus

Use inert filenames and symlink display values containing the five HTML-sensitive
characters, whitespace, `#`, `?`, `%`, Unicode, and slash/backslash lookalikes.
Literal path separators are not filename characters and must not be simulated as
one filename. Include ordinary ASCII and Unicode controls.

## Completion Rule

Before closure, update every confirmed row with the implementation revision,
test node ID, and result. Any newly confirmed consumer must be repaired in this
package or explicitly blocked with operator direction; it may not be silently
deferred. Reviewed non-consumers remain out of test scope unless the patch
touches them.
