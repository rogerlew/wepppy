# AgFields Rotation Synthesizer Fixtures

These two management files are exact copies of the source inputs used for
sub-field 3733 in the `sacral-self-discipline` AgFields failure.

Retrieved: 2026-07-10 19:26 UTC

Source directory:
`/wc1/runs/sa/sacral-self-discipline/ag_fields/plant_files/`

- `canola_spring_mt.man` was `canola,spr,MT,_cm8-wepp.man`.
  SHA-256: `819e32163aa4572113c5cd6d3d0002d1d885989a3bc885454cba5787650b3582`.
- `oats_spring_conventional.man` was `oats,spr,_CONV,_cm8-wepp.man`.
  SHA-256: `b3860d9d88cad9527c11c7d1e9dca52749022bf2a7c9c520f214b72c1affc4f2`.
- `canola_spring_mt_2017_1.man` is the preserved Jim-interface source before
  downgrade. SHA-256:
  `b29d866b1b2e0c4e21b4ce921037b58ecc67afaab077f69fc0eadeb9cda58d6c`.

`p3733_schedule.json` records the run's one-canola-plus-sixteen-oats source
sequence without retaining unrelated project or user data. Tests load only this
directory and never depend on `/wc1`.

Known pre-repair signature:

- 17 simulation years.
- 50 plant scenarios (`ncrop`).
- 136 operation scenarios (`nop`).
- WEPP error: `ncrop read as 50. Must be between 1 and 20`.
