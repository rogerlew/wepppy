# U9 independent scientific review

Disposition: the U9 actual-load handoff is scientifically supported by the reviewed source, independent analytic controls and four complete seeds. **Release promotion remains blocked**, including the separately confirmed DEPEQS coordinate mutation (U11) and all remaining final-candidate broad gates. This is not a whole-matrix review.

## Source and numerical contract

DEPOS reconstructs load as L=C-DU*(x+qostar)/phi. A root stored at native REAL coordinate precision can have C unequal to the actual returned L. DU0 therefore replaces the actual boundary load with capacity; U8's retained true-input reference demonstrated a roughly30ppm jump even after polynomial cancellation was fixed. U9 selects DU from the actual load using double intermediates and one REAL rate conversion. This closes the confirmed boundary contract defect without changing the governing equation.

The small positive DU from a supported low-side root must remain: clamping it to0 recreates the mass jump. Its tiny pre-crossing continuation is checked against the independent solution rather than hidden by a tolerance increase. Negative-flow wet intervals require the same consistent physical signs phi/(x+qostar)>0, with no integration across the zero-flow terminal.

At exactly x+qostar=0, a finite DU cannot encode unequal L and C. An explicit diagnostic failure preserves evidence instead of silently discarding load. Equal L=C can retain DU0; DEPVAL's regular no-inflow branch ignores the homogeneous boundary contribution and retains the origin limit. The added unequal-singular failure itself was not reached by the valid controls below. Any real consumer reaching it remains a promotion blocker requiring explicit accounting.

Reviewed native source SHA-256:
- erod.for `422d30692ac31327ee01a9ef8ea83b9543c46f9c1f985434fbd9037720847814`
- runge.for `9d450d55beca548c714925d309774e9a4d0d8a40e08b248a413f187b31dc31bb`
- depeqs.for `0b8229de965954d88e085c80644ac52c2bbab8c072877a4d0acdc28237a55d62`
- depos.for `7be71b278baeacefe56a4aae0bfb31dcee572636b9724eb62ea71219c847703a`
- route.for `a42733e1d56e072b4b6032d26899184654d47380edb7070f3dfa95ca5e338650`

## Independent checks

Existing suites rerun against native U9 sources: **193 passed in5.49s** (65 EROD,15 actual caller chain,113 deposition).

Additional actual-ROUTE probes, with observation-only temporary source copies and no physics mocks:
- Physical negative through-flow q=-2,phi=-2, qin2,qout1, cancellation-capacity transition. Small positive DU=4.04507894e-12 carries the actual load. First endpoint native9.99999372e-8 versus70-digit independent9.9999934361147757e-8; outlet native9.7669371257e-8 versus independent9.7669370123e-8.
- No-inflow immediate transition: C=.1*x-.01*x*x,theta=.1,D0,L0=0. Native first-grid load.000999500044 and outlet.0950000063 match the regular solution L=.1*x-.005*x*x.
- Six Case4 closing-capacity probes q=-.03,-.02,-.01,-.009,-.001,-1e-5 complete with dry export0 and no new singular/representability failure. Three exercise actual handoffs before the terminal; the shorter wet domains bypass that handoff and do not establish singular-branch coverage.

Evidence: `/tmp/review_u9_probes.py`, `/tmp/erod-u9-science-probes.json` (including source hashes, full traces and independent negative-flow reference values).

## Four complete seed outputs

Independently rehashed generated inputs, outputs and linked G1 source records for all four16-year seeds. All unchanged input assertions pass. All four existing physical audits pass, and water/soil outputs remain byte-identical to G1.

Candidate binary SHA-256: `f7b3d9d7e35d2b84ed911f9ee43796aaf2a08d54fab990657cba871e3779c5a7`.

Annual export differences versus the linked G1 records:
- ordinary: +.0039600000kg/yr, one reported export increment;
- buffer_cap: +.0431052294kg/yr, one increment;
- DEPEND failure seed: +.0431052294kg/yr, one increment;
- buffer control: unchanged.

Re-executed the current Decimal all-EVENT audit: **4 cases,1306 EVENT rows,1036 positive rows,zero flags**. This does not close the two previously retained whole-matrix normalization discrepancies unless their exact rows are shown to pass or are independently explained under the frozen acceptance contract.

Evidence: `/tmp/erod-u9-seed-hash-review.json`, `/tmp/erod-u9-seed-particles-review.json`.

## U11 finding and supported repair boundary

Implementation review confirmed that DEPEQS mutates a valid near-terminal coordinate by a fixed1e-6 offset whenever abs(x+q)<1e-7. This can move evaluation upstream of the anchor and produce incorrect loads. U9 does not repair it.

Minimal supported contract advised to the implementer:
- Preserve every nonzero wet coordinate; remove the approximate-coordinate mutation.
- DEPOS exact Case4 terminal uses the existing dry-zero load/rate convention, with strict wet comparisons for grid and no-grid branches. The no-grid dry path must also set DL0.
- q=0,x=xu=0 retains its explicit regular-origin rate phi*(k*b-theta)/(phi+1).
- A direct DEPEQS negative exact-terminal rate is outside a strict-wet API and can fail explicitly: for some physical negative phi the rate diverges while terminal load is0. The actual caller need not request it. DEPEND rootsearch has a separate existing terminal contract.
- XINFLO floors Case4 abs(qostar) at1e-5. Keep tiny-q analytic counterexamples, but add a representative q=-.001 endpoint XE=-q-5e-8 to prove the same defect within generated caller inputs. Include phi=-.5 and-2, old-trigger neighbors, exact terminal, dry side and unchanged coordinate assertions.

Full Roads840, downstream348, native broad suite, Disturbed, Cedar and expanded particle checks must belong to the exact final repaired binary. No prior candidate's green result substitutes for those gates. No production source edits or release promotion were performed by this reviewer.
