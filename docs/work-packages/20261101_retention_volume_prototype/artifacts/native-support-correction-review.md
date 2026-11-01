# Native support and ordering correction review

Disposition: **confirmed reader-assumption defects; additive readback correction warranted without model reruns.** The executed reader, declaration, reviews and failed receipts must remain preserved. This reviewer missed both assumptions during prereview; the synthetic controls repeated the assumed geometry/order and therefore did not detect them.

The actual pinned input.for adds 200 mm to the final supplied horizon unconditionally at line 572, before the 1800 mm cap at line 591 and conversion to meters at line 621. Its lines 700–728 rebuild the profile on a 200 mm grid using rounded millimeter comparisons. Initial tillage boundaries are 100/200 mm (input.for lines 956–957); tilage.for remaps the first grid layer into these two computational layers and retains the deeper grid layers.

Therefore each declared 400 mm serialized profile becomes 600 mm native support with four computational layers per OFE. The 1400 mm profile becomes 1600 mm with nine layers. The earlier SIFT 1800 mm case hit the cap and concealed this extension. This is existing pinned model behavior, not a new soil-file mutation. Source-file depth, native support and observed output depth must remain distinct in the additive reader.

The completed first baseline trace independently confirms cumulative depths approximately 0.1, 0.2, 0.4 and 0.6 m, with the last value 0.6000000238418579 m from native REAL arithmetic. Its 84 records comprise three OFEs, each containing six SCON tags for each of four layers followed by four WBH initialization tags. WBH is interleaved by OFE: sequence 25–28 completes OFE 1, then OFE 2 SCON begins at sequence 29. The executed reader incorrectly placed all OFEs' WBH records after all SCON records.

A versioned reader must enforce the corrected per-OFE phase order and independently predicted supported geometry, then retain all other arithmetic, operand, calendar, finite-output and provenance checks. Re-read completed artifacts into a new result root after all twelve declared processes finish. No new model invocation or edits to executed evidence are needed. Synthetic controls should cover the corrected 600/1600 mm native supports and reject the original invalid ordering/support assumptions.

Private source SHA-256 identities: input.for `362a328510298eb86f682b248256ae43c8b36ca15b6cf2d6dd1887999ae275df`; tilage.for `22922a276bb3ce157fc0b180c40993d63ba4b31301836d68c3fcabb2ca3b1420`. No native source text is reproduced in this public review. No raw or native files were written.

## Independent v2 readback and bottom-layer rounding

An independent read-only v2 replay accepted the first ten completed histories, each with 17,532 daily keys and valid initialized-domain flags. The 85-percent case then failed its original absolute input-mass tolerance. All twelve original process receipts independently show return zero/completion with matching consumed-input and stdout/stderr hashes. This additional failure is reader interpretation, not evidence authorizing a rerun.

The bottom layer's observed RFG is 0.849999725818634. Exact binary32 reconstruction from pinned INPUT explains it: converted 1600 mm endpoint is 1.600000023841858 m; after the 200 mm first horizon and six subsequent 0.2 m subtractions, remaining source thickness is 0.19999997317790985 m. Repeated grid addition gives final computational spacing 0.20000004768371582 m. The binary32 ratio is 0.9999996423721313, whose product with binary32 0.85 exactly equals the observed RFG. The same remapping scales bottom-layer FC/WP and BD. Reconstruct this source-bound arithmetic in a new reader revision; do not silently widen the old tolerance. Keep v2 failures and identities intact.
