# Soil anisotropy tracker

Active plan: [soil_anisotropy_execplan.md](prompts/active/soil_anisotropy_execplan.md).

M0–M2 complete on forest. Accepted contract ancestor `a94028e78`; both independent reviews approved. WEPPpy base `298e434d3`; native base `bd63094`. Rust kernel, persisted inputs, eligibility controls and single-read preparation are implemented. Blank settings preserve defaults. Bottom-depth classification is the stated implementation assumption; no horizon splitting.

M3 complete: real forest preparation proves two OFEs with 25/25/3 and one read/write, source unchanged. Rust crate tests pass (107 unit + 17 integration); all 968 Jest tests pass. Browser/API acceptance passes, including specific HTTP 400 rejections and normal download hash parity. The actual RQ worker produces byte-identical soil output. Independent review has no open SA-01 findings. Runtime candidate `e6004b118`, native `822b6fe`; test-only `2da8e9298` adds two passing crossing-horizon cases. The broad Python run had 10,461 passes/126 skips and one unchanged catalog timing failure; the failed module and all remaining tests pass on rerun (207 cases). The original gate failure, existing npm lint/core typing and optional isolation-scanner limitations are recorded in `artifacts/validation.md`. Forest web/RQ health checks pass; paired native startup pin is included.

Production and push remain out of scope. Preserve the unrelated i-crews local edit.
