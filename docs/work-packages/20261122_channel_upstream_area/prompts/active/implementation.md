# Restore cumulative upstream area at each channel head

## Purpose and milestones

In weppcloud-wbt, repair HillslopesTopaz so netw.tsv reports the cumulative area draining into each reach's upstream cell, excluding itself. In Peridot, exercise the existing consumer using a small watershed with distinct cumulative and lateral areas. Verify regenerated geometry and WEPP slope inputs. Publish Peridot and retain the SHA and evidence. Work follows docs/prompt_templates/codex_exec_plans.md.

## Progress

- [x] Diagnose the historical field and select compatible semantics.
- [ ] Correct the producer and check independently counted areas.
- [ ] Exercise Peridot and generated inputs, publish and record outcomes.

## Surprises & Discoveries

TOPAZ excludes the receiving cell. A flow accumulation raster including self requires subtracting one cell before converting to square meters.

## Decision Log

2026-11-23 02:59 UTC. Restore the original areaup name and meaning. Changing the regression would conceal incorrect metadata for other consumers.

Operator expanded scope to repair SWAT+ drainage area selection and TOPAZ joins. Verify depth and both width modes in generated TxtInOut files.

## Validation and recovery

Run the WBT fixture through HillslopesTopaz and compare every upstream-node count with independent D8 tracing. Read the generated network through Peridot and inspect serialized width. Record exact commands and outputs in the package. Revert the candidate commits to roll back software. Preserve historical inputs and outputs together.

## Outcomes & Retrospective

Implementation in progress.
