# Native soil input capacity evaluation

Status: evaluation complete; no production promotion authorized.

## Purpose and scope

Evaluate retaining more than ten SSURGO input horizons without changing native
calculation capacity, depth limits, physical parameters, or output formats.
The operator authorized this evaluation on 2026-11-18 after run
`quasi-religious-allotment` on wepp1 failed when insertion of the required
200 mm boundary produced an eleventh horizon. Zepol mukey 376873 has ten
unique horizons ending at 8, 15, 30, 56, 69, 89, 117, 190, 226 and 290 cm.

The deliverable is a bounded native prototype, reproducible generated-output
comparisons and a go/no-go recommendation. Deployment, vendoring, changing the
Python ten-layer contract, and accepting a new production capacity are separate.
This is a faithful reader-storage separation experiment, not replacement physics.

## Contract and rationale

Keep `mxnsl=10` for calculation arrays and outputs. Explore a separately bounded
input capacity. A global increase is rejected for this evaluation because fixed
output offsets assume ten layers and optional output can write past `treal(96)`.
Prefer preserving input records to introducing a new horizon-merging heuristic.
Existing ≤10-horizon inputs must preserve calculation state and numerical output.
Newly supported inputs must be read in full, including correct following OFEs and
restrictive records. Excess counts must fail explicitly.

## Complexity and security

Complexity budget: one native reader change, one input limit, and evaluation
fixtures/harnesses. No dependencies, services or deployment changes. Security
impact: low (bounded file parsing); bounds-checking and malformed-input checks
are required. Dedicated security review is not required for this evaluation.

## Acceptance

Build baseline and candidate from the same default-branch source and compiler.
Prove unchanged ≤10-layer behavior, consumption of eleven and maximum-capacity
horizons, rejection above capacity, and correct 200 mm normalization semantics.
Use native generated artifacts, not exit status alone. Record broader release
validation still required before promotion. The run-cache data is supplementary;
a deterministic committed fixture must reproduce the capacity boundary.

See [completed plan](prompts/completed/evaluation_execplan.md) and [tracker](tracker.md).
