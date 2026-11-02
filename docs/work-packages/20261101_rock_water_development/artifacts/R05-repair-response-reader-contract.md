# Snow-cap response reader contract

This original reader implements the [scientific preanalysis](R05-repair-response-science-preanalysis.md). It performs no native execution and grants no physical or release admission. Frozen runners, schemas, readers and prior evidence remain unchanged.

## Inputs and execution gate

`read_snow_cap_response.py` accepts `--campaign`, `--prior` and `--out`. The campaign is the declared 21-history snow-cap root; the prior root is the completed `R05-water-v3` campaign. Final mode requires campaign aggregate completion. Completed-case mode (`--case <declared-name>`) may run earlier only when every declared lane receipt for that case passes, including its r4 counterlane when declared. The output root must not exist. Execute only after independent approval of this response reader; final mode additionally requires aggregate completion:

    /usr/bin/python -B docs/work-packages/20261101_rock_water_development/artifacts/read_snow_cap_response.py --campaign <completed-snow-cap-root> --prior out/rock-water-development-20261101/R05-water-v3 --out <fresh-response-root>

Final mode requires passing aggregates, complete 21/12 lane records and 9/6 paired readbacks, exact case identities, actual build/run approval bindings, seven-file candidate clean/observed parity, and preserved r4/a8 ordinary-output bridges. It hashes bound traces, cached readbacks, ordinary outputs, consumed inputs and helpers before analysis and verifies them again afterward. A failed or incomplete read cannot produce a passing receipt. Retain any partial output directory on failure.

Completed-case mode emits a provisional `case-receipt.json`, two comparison files and hash-bound selective extraction caches under its fresh output root. It claims no 21-history completion. Final mode accepts repeated `--completed-case <case-output-root>` arguments, verifies each case against the final aggregate and exact input/output/helper identities, and reuses those results without decoding completed traces again. Extraction caches bind trace, schema, calendar, windows, decoder, response helper and payload hash. Earlier per-case inputs remain immutable; only the fresh analysis root is writable.

## Distinct comparisons

Each of six cases receives `a8-to-cap.json` and `r4-to-a8.json`. The first compares final-a8 observer against observed cap candidate after clean-candidate seven-file parity. The second uses the three declared fresh r4 counterlanes where available; otherwise it uses the retained completed R05 baseline/candidate pair. Historical a8 outputs must equal the current observer's outputs, and fresh r4 outputs must equal the retained r4 outputs. These checks establish explicit ordinary-output bridges, not identical internal state merely from output parity.

No favorable final-a8 comparison substitutes for the r4-to-a8 behavioral comparison. The original contrast's missing new diagnostic operands remain explicitly unavailable; selected source-stage attribution is not fabricated for older traces.

## Quantities, units and time

Validated cached daily ledgers supply native soil liquid/ice, canopy/residue stores and owned water fluxes. The reader rechecks their exact arithmetic, component sets, date/OFE uniqueness and consecutive-day continuity without repeating the full native causal reader. Native depths are converted from meters to millimeters; flux volume uses actual emitted local OFE area. Snow remains separate because incoming melt is already a liquid input. Signed residuals are reported, not waived. This is not pond or all-storage closure; B03 pond/carry findings are separate evidence.

Ordinary WAT, ELEMENT, EBE and loss files use the existing validated parsers. WAT Q volume uses cumulative contributing area only after confirming no contour scenarios. Other local water quantities keep their local-area basis. ELEMENT SedLeave and EBE Sed.Del are kg/m of emitted width and are converted to kg with the actual slope width. Sediment leaving different OFEs is never summed as independent hillslope export. Existing event/annual loss reconciliation and print bounds remain visible; no new tolerance is introduced.

Sparse events use a keyed union with explicit new/disappeared presence. Missing events contribute zero only to extensive sediment export, never to plant state or stocks. Historical Sm display absence is not converted into physical zero. Annual and full-period summaries retain both lane values, signed totals, positive/negative cancellation, first/last differences and extrema with dates. States are not summed. Exact unequal daily runs record duration, ordered sign-transition counts and the first subsequent equal day; the last unresolved episode remains open. These are represented-state persistence measures, not a new materiality threshold.

Full daily plant/state trajectories are not present in cached ledgers. The reader therefore performs a disclosed selective pass over already hash-validated traces for daily opening/closing PLANT and STATE records, declared growth/SWU/ET epochs and the next calendar day's growth epochs. It does not rerun the full flow/causal validator. LAI, root depth, carried stress and every actually recorded plant field remain source-named. Native declarations identify `rtmass` as total root mass, `vdmt` as vegetative dry matter and `rmagt` as above-ground surface residue, each kg/m2; these are not interchangeable biomass measures. Depth/height are meters and native stress/cover quantities retain their stated dimensionless meanings. Other auxiliary native fields receive no invented physical-unit conversion.

## Demand and growth interpretation

Selected EVAPPM classifications consume validated diagnostic records. Diagnostic potential basal transpiration is the exact-real expression `etorc * kcbcon / 1000`; it is not a native intermediate. Incoming Tks is actual assigned EP under the already validated source operation order. Positive potential with zero availability-limited request, positive-product underflow, canopy-covered positive request, inactive post-growth roots, skipped calls, and partial/full accepted root withdrawal remain distinct. Denominator and availability operands are retained; their values do not invent an unobserved branch.

Accepted layer uptake, native accumulated uptake and actual soil debit are separate. Their difference is decomposed into binary32 subtraction representation debit and the actual clamp debit by replaying the existing source threshold; ordinary subtraction rounding is not labeled layer zeroing. Final reported EP and the native canopy partition are reported separately from root uptake. Pre-growth demand state, actual post-growth root epoch, SWU or skipped-call evidence, daily closing plant state, next-day opening state and next-day growth records retain their native sequence identities. Missing next-day or post-growth ownership is an explicit evidence gap.

All observed selected epochs are retained for independent consequence review. Full-period daily differences outside these windows do not establish detailed formula attribution. Negative demand, unexplained positive-request skips, sediment reconciliation failures, nonzero residuals and unsupported episodes must receive explicit scientific disposition. The reader never labels carried watstr an independently validated physiological ratio and never admits or rejects a repair merely from response magnitude.

## Controls and disposition

`check_snow_cap_response.py <fresh-root>` exercises exact cancellation, annual versus full-period behavior, stock semantics, persistence/recovery, calendar/duplicate rejection, selective framing, demand partitions and underflow, actual uptake versus soil zeroing, missing ownership, cached-ledger arithmetic and identity, and sparse event mass/width handling. A retained ordinary-output compatibility probe performs no native execution or full trace replay. Pure controls prepare the reader; actual final response and independent consequence review remain pending.
