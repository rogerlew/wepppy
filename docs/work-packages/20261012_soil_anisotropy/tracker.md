# Soil anisotropy tracker

Active plan: [soil_anisotropy_execplan.md](prompts/active/soil_anisotropy_execplan.md).

M0–M2 complete on forest. Accepted contract ancestor `a94028e78`; both independent reviews approved. WEPPpy base `298e434d3`; native base `bd63094`. Rust kernel, persisted inputs, eligibility controls and single-read preparation are implemented. Blank settings preserve defaults. Bottom-depth classification is the stated implementation assumption; no horizon splitting.

M3 in progress: real forest preparation proves two OFEs with 25/25/3 and one read/write, source unchanged. Rust crate tests pass (107 unit + 17 integration); all 968 Jest tests pass. Browser acceptance, broad Python suite and final evidence review remain pending. Existing npm lint failure is tracked separately. Native startup hash pin is included in the paired release after its rejection exposed the missing update during forest restart. All four affected services are running again.

Production and push remain out of scope. Preserve the unrelated i-crews local edit.
