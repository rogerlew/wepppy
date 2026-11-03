# Dedicated Roads parameterization view proposal

Status: static proposal; human specification/layout approval absent. No production
route, API, persistence or application wiring is implemented by this artifact.

The [interactive static preview](parameterization-view-draft.html) replaces the
superseded inline five-fallback layout. Proposed product route is
`/runs/<runid>/<config>/roads/parameterization`, reached from the Roads panel. The
project's Roads controller remains the single saved-configuration authority.
The preview uses existing system-font, bordered-panel, inline-status and
Edit/Save/Cancel/Reset conventions rather than a new application shell.

## Information and scope

Show road, fill and forest/buffer role sections. Each parameter row shows meaning,
units, template baseline, ordinary adjustment arithmetic, override mode/value,
resolved input preview and a distinct native-input readback. Conductivity, Ki,
Kr and critical shear are visible without opening provenance details. Expandable
source details hold template identity, management choice and eventual hashes.

Inspecting a group never changes override scope: overrides apply to all executed
**template-owned** profiles of the chosen role; upstream land-use soils are
excluded. The example selector distinguishes gravel/loam/low/rutted profiles from
paved/loam/high/inslope road-only profiles. Example segment IDs/counts are explicitly
illustrative. Nonapplicable fill/buffer roles cannot pretend to affect a road-only
group. Inspection must use actual segment grouping in production.

Template values come from `3gloam2.sol` and `3ploam1.sol`. The gravel road Ki chain
is 2,000,000 / 4 = 500,000, before user override. Fill Ki remains 2,000,000 and buffer
Ki 120,000. Paved Ki is 5 with high traffic. The demo does not infer shear from a
filename. Low/no traffic share soil reductions but select different management.
No prepared values, hashes, execution counts or runoff/sediment results are invented.

The preview follows the proposed keys `ksat_mm_h`, `ki_kg_s_m4`, `kr_s_m` and
`critical_shear_pa`. It offers Default, Multiply and Absolute per role/parameter,
applied after ordinary adjustments. Final validity bounds and demonstrated
response ranges must agree with the canonical contract and characterization;
positive-finite validation in this local preview is not the native-representation
validator required on the server. Zero is disallowed because it invokes native
estimation rather than a zero physical coefficient.

## Actions and lifecycle

Edit creates a local draft; a sticky action bar keeps Save/Cancel/Reset reachable
on long desktop/mobile views. Reset changes the draft to baseline use, preserving
the project-bound baseline. Adoption of a newer repository baseline is a separate
future explicit action and has no simulated working control here. Save and Cancel
are local preview operations only. No network calls, browser storage, server state
or files are written by this page.

Save is disabled without changes or with invalid draft values. Dirty return navigation offers explicit Save/Discard/Stay choices. Changing inspected groups
preserves the entire draft. A simulated pending save locks editing/cancel/reset.
Readonly and busy preview modes expose inspection while disabling mutations.
Legacy unbound mode permits an explicit first Save even without override edits and
labels inspection as an unbound repository preview. Invalid saved-state mode
withholds numeric values and explains the separate repair consequence; no silent
default substitution or working repair mutation is simulated.
Production must additionally enforce server authorization/CSRF/locks, re-read
saved state on Cancel, suppress late-response draft replacement, and invalidate
Roads preparation/current results after accepted mutations.

Comparison cards distinguish baseline/custom run identities and configuration
snapshots; no output exists in this preview. Production comparisons must retain
historical labels, total and area-normalized quantities, and explain mismatched
climate/geometry/reporting periods. Observations and user targets are separate.

## Preview validation

Raw renderer, desktop/mobile screenshots and interaction readback are retained at
`/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-view-v1/`.
Run `node <raw-root>/render.cjs` to reproduce using the installed Playwright browser.

- Desktop 1440 px and mobile 390 px: document scroll width equals viewport width;
  three role sections render, no horizontal page overflow, no JavaScript errors.
- Road Ki multiplier 2: gravel preview becomes 1,000,000; switching to paved becomes
  10 and marks fill/buffer unavailable. Draft survives group switching.
- Save establishes a custom local preview; Reset returns draft Ki to 500,000;
  Cancel restores saved custom Ki 1,000,000.
- Readonly hides Edit and has zero enabled role inputs; busy disables Edit.
- Native input values remain explicitly unavailable, and comparison results remain
  empty throughout the interactions.

These are static-prototype checks, not production workflow, accessibility
certification or scientific execution validation. Independent review and explicit
human approval of the revised specification/layout remain required.

## Remaining implementation and review obligations

The preview matches the current proposed four keys, three modes, role-wide scope,
project-bound reset and no version-1 adoption action. It uses sparse in-memory demo
overrides; production sends the contract's complete 12-entry override object. The
preview does not claim to implement server payload validation, native real/format
representability checks, first-use binding, corruption repair, passive response
ownership, baseline drift comparison, artifact readback or true comparison queries.
Those states remain specified by the canonical contract and must be covered by the
approved implementation. Unbound preview and corrupt-state repair consequences are represented by preview
states. Actual native/used-run readback and comparison queries remain unavailable
until backed by artifacts; review their prescribed presentation before implementation.

Additional state readback confirms first unbound Save is available without edits,
then shows bound baseline inputs; invalid state shows zero resolved numeric fields
and retains explicit repair wording. No JavaScript errors were observed.

## Independent-review revisions

UX-01: validation now checks each requested value and each resolved value across
all illustrative groups, including the group not currently inspected. Overflow or
underflow disables Save and Save-and-return and shows a shared error. Full native
representation remains a server obligation.

UX-02: the sticky action bar is before the role sections; entering Edit scrolls to
it and focuses Cancel. This keeps actions available before the long mobile list.
UX-03: the view explicitly says native soil files are assembled during Run; geometry
Prepare alone cannot provide native readback. UX-04: the shared native validity and
range explanation appears once above the roles rather than twelve times. An
absent/disabled Roads preview withholds parameters and explains nonmutating return
to enablement. It does not create Roads state or offer a fake enablement mutation.
