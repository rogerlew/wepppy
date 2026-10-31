# U11 independent scientific review

Disposition: **supported for frozen broad validation; no release promotion recommendation yet.** The strict-wet/no-coordinate-mutation repair closes the confirmed defect in the reviewed source and focused controls. Final Roads/downstream matrices, native broad suite, Disturbed, Cedar and particle-accounting gates remain mandatory for the exact final candidate.

## Findings and contract assessment

No new high-priority scientific blocker was found in this lane. DEPEQS now preserves every nonzero wet evaluation coordinate and explicitly rejects direct negative-flow terminal/dry coordinates or anchors. DEPOS owns exact Case4 terminal and dry load/rate zeros, including q=-1; it no longer requests a terminal rate that can diverge while the finite terminal load is zero. The exact q=0,x=xu=0 regular-origin rate is retained. DEPEND's rootsearch terminal convention remains separate and its existing controls pass.

Retiring the test that expected the fixed coordinate displacement is justified: the displacement changed physical support and could move the endpoint upstream of the anchor. Replacement tests check the real caller chain, retained coordinates, physical wet-domain values on both sides of the old trigger, exact terminal and dry export. Supported q=-.001 companions accompany the tiny-q analytic probes; this matters because XINFLO floors generated Case4 abs(qostar) at1e-5.

Minor non-blocking consistency observation: DEPOS's grid dry branch zeros load(i) and tc(i) but does not overwrite detach(i); the no-grid/final branch zeros DL. No downstream reader of that stale DETACH value was found outside the routine's own wet calculation, so this is not an observed mass regression. An explicit detach(i)=0 and seeded-state test would make a grid dry-rate contract complete if included.

U10's initial ROUTE capacity now shares DEPCAP and its clamping with the downstream consumers, avoiding the separately retained negative-capacity boundary mismatch.

Reviewed source SHA-256:
- route.for `83a9ddd665aab6404e09e9ff2398b194fb24694a1f87d1a4955306f8f8d57f68`
- depos.for `7bac841e26c99c3f3b785e07f543469ddfa2e9bc01fd9d89f776a4f304e8f6f0`
- depeqs.for `87d9cfab09f759c17e37d0044fe3654191810a4154fa39d76db245e7d53ded30`

## Independent source validation

Reran native EROD, actual-caller boundary, and deposition suites: **209 passed in5.81s** (65+26+118).

Added external probes at the closest representable REAL coordinate below the supported q=-.001 flow terminal, with phi=-.01,-.5,both immediate neighbors of-1,-1,-2,-10,-1000. All16 DEPEQS/DEPOS calls complete and preserve the input coordinate. All representable nonzero rates agree with the independent80-digit ODE solution within4.5e-8 relative; all loads agree within3.15e-8 relative. The phi=-10 rate of about-3.53e-61 correctly rounds below native REAL range to zero, without changing the representable load.

Evidence: `/tmp/review_u11_probes.py`, `/tmp/erod-u11-science-probes.json` (full inputs/results, independent references, observer source hashes).

## Complete seed output review

Candidate binary SHA-256: `a4b9e7de28e3ebc813e844124547248da99f664c76613d5ef5d0b37b753edf38`.

Independently verified all generated-input hashes, linked G1 source-record hashes and output hashes for all four16-year seeds. All four existing physical audits pass. All water and soil files remain byte-identical to G1. Annual export changes versus G1 are unchanged from U9: ordinary +.00396kg/yr, buffer_cap +.0431052294kg/yr, DEPEND seed +.0431052294kg/yr, buffer control unchanged (each nonzero difference is one reported export increment).

Re-executed the frozen Decimal particle audit: **1306 EVENT rows,1036 positive rows,zero normalization/class-bulk flags**.

Relative to U9, both buffer seeds have identical output hashes. The DEPEND seed changes LOSS/PASS; the ordinary seed changes PASS/ELEMENT/EBE. Their annual metrics and seed physical gates remain consistent; broad event-level comparison still belongs to the final candidate review.

Evidence: `/tmp/erod-u11-seed-review.json`, `/tmp/erod-u11-seed-particles-review.json`.

## Remaining promotion conditions

The strict-wet failure messages must not be dismissed if a broader valid consumer reaches them. Trace and resolve any such input rather than reinstate coordinate movement or silently ignore the stop. Retained whole-matrix particle discrepancies also remain under the frozen accounting gate until the exact rows pass or have an independently justified explanation. No whole-matrix completion is claimed here. No repository sources were modified by this reviewer.
