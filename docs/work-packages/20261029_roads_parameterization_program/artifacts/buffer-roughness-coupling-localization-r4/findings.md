# Buffer roughness changes the modeled upstream response

The original roughness study **failed its upstream-isolation criterion**. Four
observation-only replays now establish the executed native feedback: buffer
roughness changes the routing group's terminal plane and duration, which changes
upstream peaks and rill width; that width changes hydraulic calculations in the
next storm. This supports a whole-hillslope response study, not an isolated-buffer
interpretation or an accepted parameterization.

This evidence concerns the selected Denver/1718465/outunrut/paved/high modern
case, using the existing U12 `erosion_road_cap` candidate. That candidate already
conditions road erodibility and upper-200 mm road conductivity; it is not raw,
unmodified generated soil. The only experimental state override retained initial
buffer RRC. Inputs, density equations and the routing law were unchanged.

## Executed chain

On simulation year 4/day 233, the off mode finalizes the connected group using
OFE 3; holding initial roughness produces no buffer outlet runoff, so the on mode
uses OFE 2 as the terminal plane. The finalization owner remains OFE 3. IRS
assigns the group's duration to the upstream OFEs and computes their peaks from
their runoff and geometry. These assignments reproduce the native REAL values
exactly. Stored values before the assignments are not presumed to be independent
upstream hydrographs.

- Shared duration changes from **183.735855 to 1,532.011597 seconds**.
- Road runoff depth is unchanged on that event, but its computed peak changes
  from **942.874211 to 113.079954 mm/h**.
- The observed native width calculation leaves road width at **156.487361 versus
  82.299195 mm**, and fill width at **179.754704 versus 150.000006 mm**.

The last observed width on day 233 equals the first width consumed on day 243
in all four road/fill mode comparisons. On day 243, the observed width changes
produce different equivalent friction and flow coefficients. At each upstream
QINF call, **the effective flow coefficient ALPHA is the only changed input**.
Returned runoff differs by −0.000544824 mm on the road and −0.001258217 mm on
the fill (on minus off). This is an observed native function response; the
nonlinear QINF law was not independently solved by this localization.

```mermaid
flowchart LR
    A[Buffer roughness] --> B[Group terminal and duration]
    B --> C[Road and fill peaks]
    C --> D[Native rill-width update]
    D --> E[Next-storm friction and ALPHA]
    E --> F[Recession infiltration and runoff]
```

The [paired table](paired-observations.md) and [numeric summary](summary.json)
retain both modes and units. In that table, ALPHA denotes the local RDAT
coefficient; the QINF comparison above uses the effective equivalent-plane
coefficient, which can differ from that local value. Native call support differs between modes,
including buffer hydrology calls; an absent call is not a zero observation.

## What passed and what remains open

All four full 16-year replays reproduce **28 ordinary output files and four
complete state traces byte-for-byte** against the corresponding retained `u1b`
modes. Canonical physical and unchanged strict particle audits pass. Independent
readbacks verify ordered producer ownership, IRS assignments, width selection
and spacing limits, equivalent friction and ALPHA arithmetic. Width power-law
candidates and QINF outputs are observed producer values, not independently
solved nonlinear laws. See the [scientific readback](../buffer-roughness-coupling-localization-r4-independent-full-readback.json)
and [implementation readback](../buffer-roughness-coupling-localization-r4-implementation-readback.json).

The original campaign still has only four completed first-pair runs and a failed
paired-isolation gate; its remaining 32 runs were not executed. The earlier
coverage attempt added one completed off-mode run. Neither campaign history is
rewritten by the successful localization. No release or production input changed.

This establishes native coupling in this selected case. It does not establish
physical correctness of shared-duration routing, the physical suitability of
100 mm roughness, a new native defect, or the decomposition cause of later
residue differences. No annual magnitude criterion or scientific tolerance was
changed, and no whole-nine-pair outcome is claimed.

The next recommended study is a **fresh, predeclared 36-run whole-hillslope
response comparison** on the same nine pairs and single RRC rule. Treat upstream
hydraulic and sediment changes as endogenous responses, while retaining exact
input, off/null, density/porosity/driver and physical gates. The failed campaign
remains reference evidence; it cannot be retroactively passed. Such a study is
model sensitivity, not physical validation of the shared-duration law.

[Reproduction and evidence boundaries](reproduce.md) describe the source-free
readback. Complete source, build, trace and failure evidence remains private.
