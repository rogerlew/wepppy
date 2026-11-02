# F04-v3 scientific readback

Date: 2026-11-01. Independent read-only review; no new model runs or evidence mutations.

**Disposition: bounded frost-policy decoupling demonstrated; production adoption deferred.** The same-source gate intervention changes cold-fixture frost activation while its warm and already-enabled controls remain exactly invariant. This supports further development of an explicit frost policy separate from conductivity configuration. It does not justify globally restoring frost.

## Evidence integrity and controls

Independently verified all declaration dependencies, both complete post-build inventories, all 16 run input inventories, and recomputed all 16 complete water readbacks and seven-file output hashes. The built baseline is SHA-256 `b226c68cc4f95bb7b0e6d92b9a8dda0589a0354be790b5073c0f0f1ead3b28d2`; candidate is `9d0f0dfa27a8678ff602719a1eb115d9e7e98a382fcf96226f17f4787eecc8e4`. They are the separately clean-built source pair, not the earlier released or Roads-observer executable identities.

All 16 cases complete successfully, with eight exact plain/debug output pairs. Both warm and KS1 baseline/candidate controls have exact hashes for all seven ordinary outputs. Initial debugger observations show native land use 1 throughout, three OFEs for Roads and one for the other fixtures. Effective KSFLAG is 0 for cold Roads, cold eRMiT, and warm; it is 1 for the positive control. Recorded initial frost depths are zero. Initial snow and fine-layer ice were not observed and are not asserted zero.

Cold KSFLAG-0 baseline runs have no frost entry; their candidates do. Both KS1 runs enter frost; neither warm run does. Witnesses have the required native completion, entry address, breakpoint state, and zero exit code. These results isolate the declared gate change within the paired source/input design, without changing conductivity flags within any pair.

## Quantified cold responses

| Observation | Roads baseline → candidate | eRMiT baseline → candidate |
| --- | --- | --- |
| Calendar support | 5,844 days × 3 OFEs, both | 731 days × 1 OFE, both |
| Positive reported frozen-water OFE-day rows | 0 → 1,204 | 0 → 39 |
| Distinct calendar days with any positive reported frozen water | 0 → 711 | 0 → 39 |
| Maximum reported frozen water | 0 → 26.54 mm | 0 → 31.23 mm |
| End-of-history reported frozen water | Zero for every OFE, both | Zero, both |
| Total runoff, final native summary | 69.18 → 69.18 mm | 26.75 → 27.53 mm |
| Average annual sediment leaving profile | 9.747 → 9.747 kg/m width/year | 109.036 → 112.025 kg/m width/year |

Runoff totals above sum the final `H1.loss.dat` rain-storm and winter-event runoff amounts: Roads 48.93 + 20.25 mm in both treatments; eRMiT 26.75/27.53 + 0.00 mm. Sediment quantities use its explicitly labeled average annual sediment leaving profile section. Values are at printed precision. eRMiT runoff rises by 0.78 mm, about 2.9%; average annual sediment rises by 2.989 kg/m width/year, about 2.7%. Roads summary equality does not mean byte-identical cold outputs: all seven ordinary files differ between baseline and candidate.

Independent event-output checks yield 181 Roads events and 8 eRMiT events. Summing the more coarsely printed event columns gives Roads 69.3 mm and 155.9 kg/m over 16 years in both treatments; eRMiT 26.7 → 27.5 mm and 218.1 → 224.1 kg/m over two years. These are rounded event sums, not contradictory replacements for the higher-precision native summary or area-weighted OFE sums. No area-wide frozen volume is inferred by summing OFE stocks.

## Freeze/thaw evidence limits

Candidate daily frozen-water records contain positive-to-zero transitions: 124, 285, and 189 for Roads OFEs 1–3, and 16 for eRMiT. For example, eRMiT reports 31.23 mm on source year 7 day 5 and zero on day 6. These are observable disappearance/reappearance proxies for reported frozen stock, not validated physical thaw counts. Rounding, transfer conventions, or reset behavior can also cause transitions; many Roads endpoints are near the 0.01 mm reporting scale. Air-temperature crossings and these daily values cannot resolve the mechanisms.

The experiment did not emit the detailed winter thermal series or directly observe energy fluxes, fine-layer ice/liquid, or all transfer clocks. It therefore cannot establish latent-heat closure, exact freeze/thaw timing, conservation across fine/coarse representations, or whether the additional frozen states are physically correct. Passing activation controls does not resolve the previously documented frozen-water ownership questions.

## Bounded next work and adoption decision

Retain existing production frost policy pending further evidence. Develop a separately reviewed explicit frost-policy setting while retaining legacy defaults and conductivity behavior; do not overload KSFLAG again. Any intended default change requires its parameterization ADR and validation decision.

Next, instrument only a small preregistered set of transitions from these existing histories: eRMiT source year 7 days 4–7 and one Roads cold-to-zero interval, plus one already-enabled control. Native hourly winter output can observe snow, frost/thaw depths, frozen thickness, and cycle counters, but its rounded fields are insufficient alone. Add narrowly scoped fine/coarse water and energy/temperature observations with exact source-clock ownership and noninterference checks. Test conservation with independently specified storage/flux definitions before interpreting stock disappearance as thaw.

A subsequent general-consumer panel must include a verified native-landuse-2 management/soil deck and representative crop/forest-product paths. All present fixtures actually use native land use 1. Native historical forest code 3 currently stops during initialization; product forest names do not supply that missing execution path. No empirical calibration data or withheld materials were used, and this experiment does not reconstruct the original rationale for suppressing non-agricultural frost.
