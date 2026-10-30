# Evidence review

Review type: primary-agent self-review; no independent subagent review requested.
Scope is isolated experiment code, tests and documentation, with no production change.

| Risk | Evidence and disposition |
|---|---|
| Mistaking a successful job for correct output | Rehash native inputs/outputs, parse actual reports, validate WAT calendars, compare independent sediment outputs. |
| Factorial changes more than hydraulics | All six eight-case sets retain every nonhydraulic soil field and deeper horizon; each OFE matches its selected endpoint. |
| Comparing different inputs across binaries | Legacy controls have identical run, soil, management, climate and slope hashes. |
| Missing or mis-scaled water transfer | Daily complete calendars; actual emitted geometry; cumulative surface area versus local lateral area; independent upstream/downstream checks. |
| Calling net exchange gross detachment | Report and figure explicitly use signed net exchange. PASS gross quantities remain separate. |
| Hiding native output discrepancies | 7/60 terminal budgets and 22 EBE events remain explicitly unreconciled, with unchanged bounds and exact native source audit. |
| Attributing all export to the buffer | No particle-origin claim; source/sink signs reported, Charleston qualified. |
| Accidental change in the preceding roles endpoint | Six endpoints reproduce all seven native output files byte-for-byte. |
| Aggregation implementation error | Focused unequal-area/unit tests plus independent DuckDB reaggregation of six endpoint sediment, runoff and percolation budgets. |
| Treating historical bedrock heuristic as a conversion bug | Inspected current writer and documented SSURGO history; report distinguishes the intentional `/1000` proxy from um/s-to-mm/h conversion. |
| Overgeneralizing diagnostic cases | Four climates/four specimens, selected panel; no field validation, candidate acceptance or broad matrix success rate claimed. |

Follow-up: isolate lower-boundary drainage/storage under fixed erosion parameters;
trace native export-accounting branches before strict event attribution. These are
scientific follow-ups, not authorization to change production soil defaults.
