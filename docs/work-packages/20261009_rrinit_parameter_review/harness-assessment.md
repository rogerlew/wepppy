# Existing Disturbed Harness

2026-10-09 UTC. Roger identified the existing ranking harness as a possible
scaffold. Confirmed: reuse it rather than build an independent matrix runner.
This is inspection and a synthetic parser probe only; no simulations or harness
implementation changes were made.

## Entry Points

- tests/disturbed/test_disturbed_matrix.py: generation and simulation matrix.
- tests/disturbed/conftest.py: input locations and isolated temporary run tree.
- tests/disturbed/analyze_matrix.py: burned/unburned event and aggregate comparisons.
- tests/disturbed/analysis_results.md: historical tables, not WEPP 261009 evidence.
- tests/disturbed/PLAN.md: original design, with some fixture descriptions now
  contradicted by the actual input bytes.

The current matrix is four textures, four severity states and five vegetation
classes: forest, deciduous forest, mixed forest, shrub and tall grass. That is
80 simulations, each configured for 100 years. Young forest is absent.
Management templates and canonical soils come from the repository; soils are
converted to 9002 with disturbance lookup replacements. Climate and slope inputs
are committed under tests/disturbed/data, meeting the committed-resource rule.

## What the Existing Tests Establish

The simulation tests assert successful completion and PASS/graph output presence.
Despite their names, the severity_gradient tests at lines 404-446 check successful
execution, not numerical runoff or erosion ranking. Ranking resides in the
separate analyzer. Its forest-family directionality table labels a case correct
when burned matched-event totals exceed unburned for runoff, sediment and summed
event peaks; that is not a full low/moderate/high ranking or physical validation.

Do not carry forward directionality alone as acceptance: the historical table
labels forest high-severity peak ratios near 193,000 as directionally correct.
Those are historical reported ratios, not verified behavior of the new release.

## Changes Needed Before RRINIT Use

1. Pin wepp_261009 rather than latest (test_disturbed_matrix.py:364), with paired
   binary hashes and a durable case manifest. Keep the generic test's current
   public behavior separate from a release-specific study configuration.
2. Stage explicit hourly context. The matrix fixtures do not create wepp_ui.txt,
   and run_hillslope does not create it. main.for:163-169 selects ui_run=0 when
   it is absent; hourly MIXPEAK eligibility requires ui_run=1. Stage the matching
   committed supporting context instead of inheriting host-private run files.
3. Add young forest and an rrinit dimension. Mutate the parsed initial-condition
   field before multi-year serialization; reparse generated .man files. Hold
   rhinit and other within-cell parameters fixed. Preserve class-specific soils
   and covers between burn/vegetation cells. Record lookup/override precedence:
   the current harness loads templates directly, not the full generic ini.data
   override workflow.
4. Replace or adapt the legacy peak reader before interpreting new results.
   analyze_matrix.py:219 assumes a five-line header and reads the year from
   lines[1]. A synthetic legacy EVENT returns one peak record; adding the valid
   v3 version marker makes it return zero without error. Reuse the released
   native reader rather than strip components or introduce another parser.
5. Preserve unpaired events. Current comparisons intersect event dates at lines
   349 and 412. Report full-record totals independently, paired-event differences,
   and burned-only/unburned-only counts. Do not silently zero-fill missing records.
   Treat peak distributions and maxima as peak metrics, not summed discharge
   volumes. Fail explicitly on malformed data instead of silently skipping rows.
6. Include effective daily rrc and first-year/later-period summaries. Add one
   gentler profile so the study can expose the depression-storage pathway.

## Important Slope Correction

The committed slope file is:

```text
2023.3
1
201.6836 102.4 1163.4
6 87.9
```

The model reads aspect and width from the third line, then point count and
length from the fourth (input.for:383-399). Thus 201.6836 is an aspect, not a
201.68 m slope length. Length is 87.9 m. The listed profile's length-weighted
mean gradient is 0.385601965, approximately 38.56%, using the same linear-segment
integration as profil.for:37-45. The documentation's approximately 200 m/43%
description is not authoritative for these bytes.

At that average slope, IRS depression storage is zero throughout the proposed
0.006-0.10 m effective-roughness range. The existing profile remains useful for
erosion/ranking, but alone cannot reveal that storage sensitivity. Retain it
as a control and add a reproducibly generated 20% profile with the same length
and width; do not silently change the historical fixture.

## Revised Scaffold Recommendation

Keep the existing four textures and five vegetation classes; add young forest.
That yields 96 baseline cells. Current rrinit plus 0.006/0.010/0.020/0.040 m,
deduplicated within a cell, gives 448 simulations on one profile. Repeating that
grid on one additional 20% profile gives an upper bound of 896 runs before
deduplicating identical complete inputs. Start by validating baseline preparation
and a small sentinel set, then decide whether the second profile needs the full
matrix or only representative subsets.

This supersedes the earlier generic 444-run fixture proposal as the preferred
implementation scaffold, not the scientific test levels or controlled-comparison
principles. Reusing the existing climate, soils, template preparation and analysis
layout is simpler and more reproducible. Do not start the campaign or revise
production defaults without Roger's next execution direction.
