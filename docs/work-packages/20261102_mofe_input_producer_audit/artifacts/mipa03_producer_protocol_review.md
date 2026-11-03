# MIPA-03 independent producer/protocol review

Reviewer: `producer_review`, 2026-11-03 UTC. Read-only production inspection at
WEPPpy `3e4e80c6d5cff82aa7b66435050c70b28a1503e2`; no production edits.
This is discrepancy evidence for the new checkpoint, not approval of a proposed
scientific interpretation. Reference-source binding is owned by the separate
native-reference review; this review independently inspected its reader source.

## Findings

1. **High: fire-date serialization disagrees with the reference reader.**
   `Wepp._prep_firedate` (`wepppy/nodb/core/wepp.py:1736`) checks that three
   delimiter-separated tokens are integers but writes the original string.
   The UI explicitly labels the field `Fire date (mm dd yy)` in
   `wepppy/weppcloud/templates/controls/disturbed_sbs_pure.htm:162`.
   The setter route persists that value without date normalization.
   `_parse_fire_year` in `rap_ts.py:86` maps `06 01 24` to 2024 and accepts ISO
   and slash forms. Reference `src/readrap.for:59` reads three integers as
   month/day/year without expanding a short year: native fireyr becomes 24,
   while the producer scales 2024. ISO/slash strings do not satisfy that
   list-directed record contract. Native provenance alone cannot resolve this
   producer/consumer disagreement. Normalize the emitted date under the reviewed
   contract and exercise UI-supported short years, ISO/slash input, leap dates,
   invalid dates and clearing without changing the saved user value incidentally.
2. **High: stale presence files survive supported changes of mode.**
   `RAP_TS._prep_transformed_cover` creates `simfire.txt`, but ordinary
   `prep_cover` never removes it when the transform is cleared. `_prep_firedate`
   leaves an existing `firedate.txt` when the saved date is cleared. The full
   preparation service does not remove those files either. Reference `main.for`
   and `readrap.for` use their existence to select behavior. Therefore rebuilding
   the same run directory can consume the previous scenario. The checkpoint
   must cover transformed-to-observed and date-present-to-absent transitions,
   with failed/previous artifacts retained through the established conventions.
3. **Medium: the ordinary single-OFE fallback fails for hydrated year keys.**
   `rap_ts.py:400` evaluates `yr - 1` when a hillslope value is missing.
   Parquet hydration deliberately creates string year keys (`rap_ts.py:165`).
   A missing 2024 value with an available 2023 value raises `TypeError` instead
   of applying the existing previous-year-or-zero fallback. Preserve that
   fallback policy while supporting the actual key representation. Cover both
   string and integer legacy keys and `fallback=False`.
4. **Medium: the bound specialized reader reverses the last two RAP bands.**
   Both producer paths write TREE, SHRUB, PERENNIAL, ANNUAL, LITTER, BARE.
   Reference `readrap.for` reads the fifth row into `barec` and the sixth into
   `litc`. Producer order is also documented in the RAP README. Correct native
   field binding must be explicit; a successful run cannot prove band identity.
   Searches found no dynamic use of `barec`/`litc` in the inspected specialized
   physics files, so this review does not attribute a measured runoff difference
   to that reversal.

## Direct writer reproductions

Executed through `wctl exec -T weppcloud python -` against normal imported
modules. Actual cover and date writers were called on a temporary directory;
only unrelated NoDb lookups, feature authorization and translator were supplied
as test doubles. No native execution or full configured-workflow claim is made.
The evidence directory in the container is
`/tmp/mipa03-producer-review-g49ohfhr`.

Input: single OFE, each of the six bands has `{'2023': {'101': 10.0},
'2024': {'101': 20.0}}`; translator maps WEPP 1 to TOPAZ 101; date `06 01 24`;
empty-but-present transform mapping. Call `prep_cover`, set transform to `None`,
and call again. Then remove TREE/2024/101 and call again. Separately call
`Wepp._prep_firedate` with the short date, `None`, and ISO date.

Observed output:

```text
simfire_survives_return_to_observed: true
cover header: 2023 2024
six cover rows: 10.0 20.0
single_ofe_missing_string_year: TypeError unsupported operand type(s) for -: 'str' and 'int'
two_digit_fire_date_written: '06 01 24'
firedate_survives_clear: True
iso_fire_date_written: '2024-06-01'
```

These are renewed producer failures, independent of the already recorded native
9005 header and restrictive-record failures.

## Emitted protocol and intended boundaries

| Artifact | Actual producer record and ownership | Normative/validation disposition |
| --- | --- | --- |
| 9005 soil preamble | Version, comments, soil description, `ntemp ksflag` | Keep current format; no new admitted upload version. |
| Each OFE extension | `ksatadj`, quoted landuse, burn code, quoted texture label, coarse texture enum, `uksat`, `lkeff` | Both ordinary/debug serializers now derive enum from that OFE's surface sand/clay. Enum 1/2/3/4 is clay loam/loam/sand loam/silt loam. Hydraulics are mm/hour, with existing `-9999` producer sentinel for unset values; sentinel interpretation needs the bound consumer contract. |
| Each OFE soil header | Soil name, texture text, layer count, albedo, relative saturation, Ki, Kr, critical shear | Preserve values/units and existing native semantics. |
| Each horizon | Cumulative depth mm, density g/cm3, Ksat mm/hour, anisotropy ratio, FC/WP volume fractions, sand/clay/organic matter/rock percent, CEC; followed by Rosetta `theta_r theta_s alpha npar ks wp fc` | Existing serializers append seven Rosetta values for versions >=9002. Unequal-layer actual-reader evidence must distinguish OFE ownership and trailing-record alignment. No formula or retention-policy change is authorized by the existing identity contract. |
| Each OFE restrictive record | Exactly one `slflag ui_bdrkth kslast` record; depth mm and conductivity mm/hour | Native must consume exactly once per OFE; test at least two unequal-layer OFEs. |
| `p<wepp_id>.cov` | One calendar-year row; six percent-valued rows per OFE in TREE/SHRUB/PERENNIAL/ANNUAL/LITTER/BARE order | No IDs or counts appear in body. Numeric OFE order is positional and must match other decks. `_ordered_cover_ofes` requires contiguous 1..N and identical sets across all bands/years. |
| Transformed `.cov` | Earlier years retain actual observations; fire year and later use the fire-year observation times the curve at `year-fire_year`, extending the final curve value; missing transform key preserves original band; transformed values have one decimal precision | This annual transformation is existing behavior. It does not resolve native within-year fire activation or canopy units. |
| `cancov.txt` | Empty presence flag emitted by both cover paths | Prove activation and missing-file behavior in native consumer. |
| `simfire.txt` | Empty presence flag emitted only by transformed path | Intended mode selection must track current scenario, including removal of stale presence. |
| `firedate.txt` | Original saved string emitted when not `None` | Normalize its executable representation under the checkpoint; current native and producer interpretations disagree. |

`_prep_revegetation` asserts only climate/RAP minimum and maximum year agreement;
it does not compare interior years. The native reference discards the `.cov`
calendar header and consumes columns positionally. The new matrix must specify
exact year mapping and reject a missing/extra/reordered year rather than silently
binding one calendar to another. Mixed integer/string keys are permitted by the
Python type aliases but plain `sorted()` cannot order a mixture: either normalize
under a reviewed contract or reject malformed mixed state explicitly.

Full `prep_hillslopes` orders deck preparation, climates, run-file creation,
frost/phosphorus/baseflow/UI/PMET/snow companion preparation, and then RAP/fire
preparation when `Disturbed.sol_ver == 9005`. The revegetation run template
adds large-graphics output; it does not send an extra cover filename prompt.
`reveg.cfg`, `reveg-mofe.cfg`, and `reveg-10m-mofe.cfg` select different older
executables. Their selection strings are provenance leads, not acceptance proof;
the authorized task excludes changing these defaults.

## Coverage and configured-case availability

Existing `tests/wepp/soils/test_mofe_identity.py` covers real 9005 ordinary/debug
serialization and reversed two-OFE texture order. It reparses with Python, not a
native consumer. `tests/nodb/mods/test_rap_ts_cover_transform.py` covers two-digit
transform-year parsing, percent-to-management fraction, one transform sequence,
and numeric ordering of 12 OFEs in both paths. It does not exercise the failures
above, native band/date interpretation, missing/extra rows, or a full prepared
revegetation workflow. The management-preparation RAP test mocks management
behavior; it cannot establish dynamic native cover.

The committed hillslope-smoke inputs used by the existing soil test are a suitable
deterministic generator source. Generate distinct band and hydraulic histories
with OFEs 2 and 10 in a 12-OFE deck, explicit leap/fire boundaries and different
layer counts. Assert actual consumed values before comparing output changes.

A read-only shallow census of `/wc1/runs/*/*/rap_ts.nodb`, paired with saved
Wepp/Disturbed JSON state, found one version-9005 case:
`/wc1/runs/no/no-win-kingmaker` (`reveg.cfg`, single OFE, no date). It has no RAP
year range, Parquet or prepared `.sol`/`.cov` files. It is not an acceptance case.
A supported disposable fork with deliberately populated RAP state is needed
unless another complete case is identified. This census did not inspect nested
scenario roots and is not an exhaustive project inventory.

No production edits or native/scientific approval are part of this review.
