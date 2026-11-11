# Failure-class matrix - Browse output encoding

**Status**: Locally validated at `73d219877`; rollout pending
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

## Final consumer dispositions

All confirmed consumers are closed locally at `73d219877` (10 focused tests
pass). Node names below belong to `tests/microservices/test_browse_routes.py`.

| Consumers | Evidence and disposition |
| --- | --- |
| Directory row; breadcrumb; copy-path | `test_browse_directory_breadcrumb_escapes_and_encodes_stored_name`; real nested directory, empty child, exact href and copy-path readback pass |
| File row; download | `test_browse_listing_escapes_filename_and_encodes_entry_links`; ASCII/Unicode/hostile labels and byte delivery pass |
| Raster/CSV; annotated; D-Tale; schema/data; diff | `test_browse_action_links_encode_filename_and_preserve_query` (four suffix cases); encoded route/query attributes and schema GET pass; external backend execution not claimed |
| Symlink suffix | `test_browse_listing_escapes_symlink_target_text`; target text and permitted target bytes pass |
| Not-found breadcrumbs and diff | `test_browse_not_found_breadcrumb_escapes_reflected_path`; 404, inert labels, encoded path and quote/ampersand query pass |
| Trusted listing handoff | Source review: only literal Markup.format builders; no listing/breadcrumb handoff casts or safe filters |
| Sort links | Source review: complete decoded ASGI path quoted once; query encoded and href escaped |
| Pagination/showing | Source review: query values encoded, labels/counts integers/static; unchanged |
| Filter input | Source review: Markup.format replaces explicit attribute escape without double escaping |
| Manifest/virtual tuples | Source review: same tested html_dir_list renderer, no independent HTML assembly or archive behavior change |
| JSON APIs; file preview bodies | Unchanged separate boundaries; not expanded into this patch |

The preliminary source-line inventory above is retained as diagnosis provenance;
this section records the final disposition. No production-equivalent claim.
