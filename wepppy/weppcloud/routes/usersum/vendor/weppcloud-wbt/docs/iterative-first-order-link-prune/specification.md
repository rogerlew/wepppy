# Iterative First-Order Link Prune Specification

## Purpose

Define a single clean-room stream-network algorithm that performs:
1. source-area-based channel qualification, and
2. iterative first-order-link pruning with topology reclassification,

to match the current TopAZ parity target used in WEPPcloud workflows.

This is a behavioral specification, not a source-port specification.

## Recommended Tool Identity

- Rust type name: `IterativeFirstOrderLinkPrune`
- CLI tool id: `iterative_first_order_link_prune`

## Scope

In scope:
- D8-raster stream qualification from upstream area and source-area thresholds.
- Iterative minimum-link-length pruning with receiver-local thresholds.
- Topology reclassification and degeneration handling during pruning.
- Optional spatially variable threshold-code support.

Out of scope:
- DEM pit filling/breaching.
- Flow-direction generation.
- Watershed boundary extraction.

## Oracle Parity Contract

This section defines what must be captured when IFOLP behavior is validated against an oracle dataset.

### Fixture threshold provenance

Each fixture must declare threshold provenance for `(csa_ha, mscl_m)` in one of two classes:
1. authoritative: threshold values are traceable to an explicit run artifact (for example, run log or control file entry),
2. inferred: threshold values were inferred (for example, filename convention).

Root-cause closure for parity mismatches requires authoritative provenance. Inferred provenance is diagnostic-only and cannot close high/medium attribution risk.

### Oracle runtime manifest

Parity campaigns must include an oracle runtime manifest that captures:
1. oracle mode (`native_runtime` or `snapshot_copy`),
2. executable identity (`sha256`, version string, and source revision when available),
3. preprocessing contract (inputs, transforms, and ordering),
4. pointer encoding contract (including conversion rules if used),
5. NoData/indeterminate handling assumptions.

When `snapshot_copy` is used, parity conclusions are limited to raster-equivalence against that snapshot and do not, by itself, prove native-runtime parity.

## Inputs

Required:
- `--d8_pntr`: D8 flow-direction raster.
- `--upstream_area`: upstream area raster in number of contributing cells.
- `--output`: output binary stream raster (`1=stream`, `0=background`).
- `--csa`: default critical source area (hectares).
- `--mscl`: default minimum source channel length (meters).

Optional (spatial variability):
- `--threshold_code_raster`: integer code raster mapping each cell to threshold-code id.
- `--threshold_table`: table mapping code id -> `(csa_ha, mscl_m)`.

Optional:
- `--esri_pntr`: pointer encoding toggle.
- `--epsilon`: floating comparison tolerance (default `1e-5`).
- `--fail_if_only_channel_pruned`: default `true`.
- `--max_junctions`: optional non-negative integer cap on retained active inflowing stream cells per receiver.

Input validity:
- `--csa` must be finite and strictly positive (`> 0`).
- `--mscl` must be finite and non-negative (`>= 0`).
- `--max_junctions` must be a non-negative integer when provided.
- When threshold-table overrides are used, each row must satisfy finite `csa_ha`, `mscl_m`, with `csa_ha > 0` and `mscl_m >= 0`.

## Threshold Model

### Code resolution

Each stream cell resolves to local `(csa_cells, mscl_m)`:
1. if code raster/table are provided, resolve by code id;
2. otherwise use global `--csa` and `--mscl`.

### Unit conversion

- Upstream-area comparisons are performed in cell-count space.
- Cell area in hectares is:
  `cell_area_ha = (cell_size_m * cell_size_m) / 10000`.
- Convert `csa_ha` to integer cell threshold as nearest-integer cell count, then clamp to at least one cell:
  `csa_cells = max(1, nearest_integer(csa_ha / cell_area_ha))`.
- Link length in map units is:
  `length_m = length_cells * cell_size_m`.

## Internal Topology Classes

Implementation may use any representation, but behavior must preserve these roles:
- `NON_STREAM`: not in active network.
- `HEAD`: source node, downstream continuation exists.
- `MID`: through-link interior.
- `JUNCTION`: node with >=2 inflows and downstream continuation.
- `TERMINAL_HEAD`: source-like terminal.
- `TERMINAL_JUNCTION`: terminal with inflow(s).

## Algorithm

## Phase A: Source-area qualification

1. Build provisional stream mask from the minimum active `csa_cells` threshold.
2. Classify topology into the classes above.
3. For each `HEAD` or `TERMINAL_HEAD`, walk downstream and enforce local `csa_cells`:
- remove failing cells along the walk;
- stop at first qualifying cell, or at a receiver decision node.
4. Phase-A traversal order is parity-critical:
- perform a single row-major scan over current candidate source classes;
- apply state updates inline so later cells in the same scan see earlier mutations;
- do not restart the full scan mid-pass.
5. Receiver handling during this walk:
- if receiver is a junction and inflows collapse to one, demote to non-junction class;
- if receiver is a terminal-with-one-inflow equivalent, recheck local `csa_cells` and either remove it or keep it as terminal source-equivalent.
6. Phase A is a single row-major qualification pass with inline topology mutation; do not run an extra global full-grid qualification rescan before Phase B.

## Phase B: First-order-link pruning

### Link definition

A first-order link begins at `HEAD` or `TERMINAL_HEAD` and descends to first receiver node:
- receiver can be `JUNCTION`, `TERMINAL_JUNCTION`, `TERMINAL_HEAD`, or terminal edge/outlet condition.
- in terminal-head special cases, receiver may be the start cell itself (self-receiver).

Link payload semantics:
- normal case: payload contains source/interior branch cells upstream of receiver.
- receiver cell is preserved in normal deletion.
- special self-receiver terminal case may delete receiver/source cell itself.

### Length definition

- normal head starts: sum full step lengths.
- terminal-head starts: apply parity half-cell initial length behavior.
- downstream receiver-cell step is included in normal receiver-preserving link length.

### Receiver-wise candidate selection

1. Scan source starts in row-major order.
2. Build links and receiver associations in that same encounter order.
3. Receiver groups are ordered by first receiver encounter in that scan.
4. For each receiver group, select shortest incoming link using:
- strict-improvement test with epsilon (`new_len < best_len - epsilon`),
- first encountered link wins ties (no secondary tuple sort).

### Pruning rule

For selected shortest incoming link `Lmin` at receiver `R`:
1. Compare `Lmin.length_m` against receiver-local `mscl_m`.
2. If `Lmin.length_m < mscl_m - epsilon`, prune `Lmin` immediately.
3. Apply only-channel guard:
- parity guard condition: if current pass has exactly one generated candidate link and the current receiver group has exactly one incoming candidate link, and `fail_if_only_channel_pruned=true`, fail explicitly.

### Optional junction fan-in cap (`--max_junctions`)

When `--max_junctions` is provided:
1. Evaluate live receiver inflow count at each receiver group during pass-time mutation.
2. If live receiver inflow count exceeds `max_junctions`, prune the shortest live incoming link immediately (same strict-epsilon + first-encounter tie behavior).
3. Repeat within that receiver group until receiver inflow count is `<= max_junctions` or no live candidate remains.
4. This cap is additive to MSCL pruning; either condition can trigger pruning.
5. If `--max_junctions` is omitted, preserve retained baseline behavior (no extra fan-in cap pruning).

### Deletion timing and state handling

Deletion is immediate (not batched):
1. Mutate raster/state as soon as a link is pruned.
2. Re-evaluate receiver inflow condition immediately.
3. If receiver degenerates from junction-role to mid/terminal-role, set `degeneration_flag = true`.
4. Candidate links are generated once per pass from pass-start topology; do not rebuild full candidate sets after each deletion.
5. Candidate validity handling:
- allow self-receiver terminal pruning when receiver/source are the same cell,
- selected non-self candidates are revalidated against current in-pass state; stale candidates are skipped for that pass (no fallback candidate from the same receiver group).

Pass cadence (parity-critical):
1. Run one full receiver pass.
2. If `degeneration_flag=true`, normalize/reclassify topology and run another pass.
3. If `degeneration_flag=false`, terminate after the pass, even if deletions occurred.

## Determinism Rules

To preserve parity-consistent reproducibility:
1. Source discovery order is row-major.
2. Receiver evaluation follows discovery/assignment order induced by source scan.
3. Shortest-link ties resolve by first encounter under strict epsilon-improvement.
4. Use fixed default epsilon.
5. Under `--max_junctions`, repeated in-group cap pruning keeps the same shortest-link selector and tie rules at each step.

## Numeric Decision Contract

1. Default epsilon for strict comparisons is `1e-5`.
2. Phase A source-area qualification uses epsilon-tolerant threshold comparison in cell-count space (`area_cells >= csa_cells - epsilon` qualifies).
3. Phase B prune predicate is strict with epsilon in map units:
   prune when `link_length_m < mscl_m - epsilon`.
4. Near-tie shortest-link competition uses strict-improvement only:
   replace current best only when `candidate_length_m < best_length_m - epsilon`.
5. Do not add implicit rounding beyond the explicit `csa_ha -> csa_cells` conversion rule.

## Error Contract

Hard-fail with explicit errors for:
- raster geometry mismatch (rows/columns, resolution, or georeferenced extents);
- invalid pointer codes on active stream path (including `0` and any non-D8 code);
- threshold code with no table entry;
- cycles detected in any active network component during traversal/pruning;
- no channels after initial qualification;
- no channels at pruning stage where a network is required;
- only-channel prune guard violation when enabled.

No silent fallback wrappers.

## Output Contract

Primary output:
- binary raster (`1=stream`, `0=background`) for valid cells.

Background/NoData behavior:
- preserve valid NoData footprint from raster geometry as applicable.
- all non-NoData valid raster cells stay in output domain; do not remap valid cells to NoData solely by pointer-code value.

## Validation Matrix

Must-pass:
1. Short tributary at simple junction is pruned.
2. Adjacent/chained short tributaries are pruned across degeneration-triggered passes.
3. Receiver with one incoming short link can be pruned when rule triggers.
4. Terminal-head short stub follows half-cell behavior.
5. Receiver-preserving deletion in normal links is respected.
6. Only-channel guard raises explicit failure (when enabled).
7. Spatial threshold-code cases alter decisions by location.
8. ESRI pointer mode parity.
9. Deterministic tie behavior by encounter order.

## Acceptance Metrics Contract

Normative parity acceptance:
1. exact binary stream-mask equality on accepted fixtures,
2. deterministic canonical report stability across reruns.

Diagnostic metrics (triage/localization, not standalone acceptance):
1. stream-cell count delta,
2. connected-component delta,
3. junction-count delta,
4. outlet-reachability match,
5. FP/FN topology-context decomposition.

When normative acceptance is not met, record:
1. first-divergence localization (first mismatching cell in row-major order plus FP/FN classification),
2. phase-level localization evidence (candidate pass counts and available oracle-phase evidence),
3. sensitivity sweep outcomes for `csa`, `mscl`, and `epsilon` around decision boundaries.

## Behavioral Pseudocode

```text
mask = qualify_by_source_area(d8, upstream_area, thresholds)

require_non_empty(mask)

repeat:
  degeneration_flag = false

  links = discover_first_order_links_row_major(mask, d8)  # pass-start snapshot

  for receiver in receiver_discovery_order(links):
    repeat:
      lmin = shortest_by_strict_epsilon_first_encounter(incoming_live_links(receiver))
      if lmin is none:
        break

      if not candidate_is_still_valid(mask, lmin):
        if max_junctions is omitted:
          break  # retained baseline skip/fallback behavior
        continue

      mscl = receiver_local_mscl(receiver)
      cap_exceeded = max_junctions is set and inflow_count(receiver, mask) > max_junctions
      if lmin.length_m < mscl - eps or cap_exceeded:
        if parity_single_link_guard_violated(links, receiver):
          fail

        prune_link_immediately(mask, lmin)  # preserve receiver except self-receiver terminal case

        if receiver_degenerated(mask, receiver):
          degeneration_flag = true

        if cap_exceeded:
          continue  # keep pruning until cap satisfied
      break

  if degeneration_flag:
    reclassify_topology(mask, d8)
    continue

  break

output_binary(mask)
```
