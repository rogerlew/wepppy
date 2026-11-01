# Prepared flux observer source review, revision 2

Disposition: **PASS for the three prepared source files; execution approval remains pending concrete reader, runner and exact freeze.** No build or model run was performed. Revision 1 remains retained; this review binds only prepared-v2.

Independently verified all original and prepared hashes against actual files. A line-sequence comparison confirms each original file is unchanged and all edits are insertions: 55 lines in hourly WATBAL and fourteen lines in each ET routine. All 83 inserted fixed-form lines fit within column 72. No declaration, native assignment, branch, label, helper local or COMMON was added or changed. Existing BPO/BPLAYERS interfaces are reused.

Every added local operand is assigned before its observation. Both XX observations follow its assignment and the common label-60 return is reached after XX initialization even on negative-demand/residue-return paths. Neither J2, RTO nor XITFLG is read by the added observations. Both actual ET callers, WATBAL and WATBAL_HOURLY, initialize EP/ES/ERES before dispatch; EVAPPM's unassigned ERES is therefore a defined caller-owned value. Hourly PINTLV is explicitly reset before the uptake observations. No SWU-local array or XX is read. DRAINQ, WATBL and UNSDEP are initialized before unconditional drainage observations; DDRAIN is now observed only within the actual drainage-call branch.

The hourly stage snapshots correctly bracket ET, upward capacity redistribution, drainage and lateral flow. Existing final-hour overflow records complete the surface boundary. Uptake PRE/POST bracket the full decision, and SWCALL is emitted only after an actual SWU call. This records branch execution without inventing zero-valued missing calls. No native final carry or independent root uptake local is claimed observed.

Two closure requirements remain outside source safety:

- The draft ownership contract's coarse-total sentence is incorrect: coarse liquid is ST + THETDR*(DG-FROZEN), while physical coarse ice is FRZW + THETDR*FROZEN. Their total is ST + FRZW + THETDR*DG. Adding FRZW alone to coarse liquid omits dry water on frozen support. Correct the contract and require the reader to use the intended coordinate explicitly.
- FX_REQUEST/RETURN also execute when these ET routines are called by ordinary WATBAL. The strict reader must require each selected pair to be enclosed by matching FX_ET_PRE/POST, with correct day/OFE/final-hour/method and exactly one pair. Reject orphan, duplicate or mismatched internal ET records. A method ID alone is not a unique caller identity. Enforced stream nesting can establish caller context without new native bookkeeping.

Prepared-v2 source-bindings SHA-256: `d373b146b12af3bf973516ea8aca94fd89a1fab6c5edb4dd141d0827db49e90a`.

Prepared file SHA-256 values:

- watbal_hourly.for: `066b0cfce1a7d53ab740b6cc03cd51da8b987ad9c7ad4598068b110c6dde925e`.
- evap.for: `e5850f8e9e8d945c6a3decc112bb42071366e02b6f61b97290a4f674d85099a9`.
- evappm.for: `f50b5c2310ca9e1f454cb37dfe860b0f1171830b5be53b52ed6d34a936e05f12`.

Full output/FH-trace/filtered-old-BPO parity, actual linked runtime and complete new-record checks remain mandatory after exact prereview. Reviewer writers are clear after scoped documentation lint.
