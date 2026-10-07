# Warming championship legacy roughness comparison

**Status**: Closed research 2026-10-07 00:37 UTC  
**Timezone**: UTC

## Overview

Repeat the 10/17/60 cm roughness experiment with the original `wepp_260803` binaries, then compare the 10 cm legacy and corrected surface-return results. This tests roughness sensitivity and whether the peak correction preserves water accounting on warming-championship.

## Scope and objectives

Run all 864 hillslopes and the watershed for 1980–2003 in each lane. Change only the 1,885 initial-condition records originally at 10 cm. Keep the two 6 cm and seventeen 0.8 cm records unchanged. Use the frozen inputs from the completed corrected-build experiment and require byte-identical matched inputs across builds. Include fresh totalwatsed, outlet peaks and hydrographs, and hillslope water/peak comparisons. Do not alter the original project, closed packages, model source, binaries, defaults, or deployments.

## Complexity budget

Reuse the previous offline runner, semantic management parser, output validator, and scientific Python environment. Permit only a new isolated experiment directory and analysis scripts. No new services, dependencies, queues, flags, or infrastructure. Eight independent hillslope processes are bounded to a host with 48 logical CPUs and over 100 GiB available memory at preflight.

## Generated artifact validation gate

Applicable: yes. User intent is an original-build comparison at matched roughness. Durable inputs are the frozen executable snapshot, not mutable NoDb state. Record binary hashes and release provenance; parse every management file; compare every consumed input hash with the corresponding corrected lane. Retain terminal records, fresh output hashes, independently parsed flow results and figures. Recheck inputs after execution and test output-mode parity. Missing or failed outputs block quantitative claims. Completion means environment-validated scientific comparison, not deployment or general proof of physical correctness.

## Success criteria

- All 2,592 hillslope and three watershed runs plus the output-mode control finish successfully.
- Input isolation, unchanged source, negative controls, and fresh output checks pass.
- Report within-build roughness sensitivity and matched 10 cm build differences, including water-volume conservation and hillslope peak departures.
- Investigate any unexpected volume differences; distinguish source/build differences from the return patch alone.
- Deliver figures, machine-readable results, and limitations.

## Security and parameterization

Security impact: none; no service or permission changes. Dedicated security review is not required. No production parameterization changes; no ADR required. Offline experimental roughness mutations are explicitly requested by Roger.

## Stakeholders and related work

Roger Lew requested and reviews this comparison. The reference is [the completed corrected experiment](../20261006_warming_rrinit/package.md). No stakeholder email or production release is authorized here.

## Deliverables

Execution scripts, evidence, comparison figures and results will be retained under `artifacts/`; full raw outputs remain on forest at `/workdir/warming-rrinit-legacy-20261006`.

## Closure notes

All 2,596 executions, matched-input checks, negative controls, output-mode parity and 18,177 raw/derived output hash checks passed. [Results](artifacts/results.md), [validation review](artifacts/validation-review.md) and four comparison figures are delivered. The original project's 5,201 inputs remain unchanged.

The original build has larger extreme outlet-peak sensitivity to roughness. The candidate preserves long-term yield closely but increases the printed hydrograph/ledger shortfall, including an 18.30% deficit in one selected five-day event window. The scientific comparison is complete; full hydrograph and release validation remain unresolved. No model patch, deployment or stakeholder message was made in this package. Raw artifacts and reproducible scripts are retained on forest; compact evidence is retained here.
