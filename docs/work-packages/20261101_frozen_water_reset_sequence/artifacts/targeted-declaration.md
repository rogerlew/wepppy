# Retarget existing hourly observations for three reset extrema

The complete retained reset census fixes one largest positive zero-ST layer
residual per context: zero map1581 (year3 day20 OFE1 layer1), normal map1596
(year3 day20 OFE1 layer1), high map5247 (year7 day344 OFE1 layer1).
The existing binary already contains before-allocation, after-PURK and final
hourly water-balance observations, selected by buffer_observe.on. Its current
window (year16 days126–127) does not observe these events. Reuse this owned
observer before proposing any additional instrumentation.

Exactly three new full16-year processes, using the exact accepted observer
binary and all17runtime inputs. Change only buffer_observe.on to the selected
year/day; the existing observer records that day and the preceding day. Freeze
all982build members, current input identities, reader/runner/declaration and
runtime libraries. Independent scientific/implementation review precedes runs.
No compilation, model source change, endogenous state control or new dependency.

Require normal completion, all17,532daily keys, identical seven ordinary outputs
and byte-identical full FRWATC history trace against each accepted observer case.
Runtime inputs must remain unchanged. The retargeted log must contain finite,
unique, complete three-OFE/two-day/24-hour profiles at all three stages and the
actual allocated-water/flux operands. Preserve failed attempts; never shorten the
configured period, alter model inputs or tune a threshold to obtain acceptance.

Before→after-PURK includes input allocation and percolation. After-PURK→final
includes ET, capacity redistribution, drainage and overflow; it is not an isolated
ET measurement. A zero allocated input with no stage delta can exclude some
writers, but source-supported possibilities must remain distinct from observed
accepted fluxes. Treat recorded fluxes according to their actual units/timing;
profile interlayer redistribution cancels, while cumulative surface/subsurface
values must not be double-counted. No annual loss attribution follows.

Retain complete outputs privately and publish source-free stage records,
identities, comparisons and explicit unresolved links. These runs extend the
mechanism investigation by reusing an existing diagnostic window; they are not
an adaptive parameter sweep or a behavioral ablation.
