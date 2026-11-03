# MIPA-03 independent contract correctness review

Reviewer: `mipa03_contract_correctness`, 2026-11-03 UTC.
Disposition: **PASS for the pre-implementation normative checkpoint.** No
blocking high/medium contract finding remains. This is not approval of an
implementation, binary, numerical history, publication or deployment.

## Reviewed scope and authority

Reviewed the new `docs/schemas/specialized-revegetation-consumer-contract.md`,
ADR-0134, the MOFE identity/native coefficient amendments, and the operator
resolution appended to `20261103_specialized_consumer_decision.md`. The native
`docs/contracts/specialized-revegetation-consumer.md` is byte-identical to the
WEPPpy contract; the native coefficient contract cross-links its compatibility
exception. Starting revisions are WEPPpy `ea5d4cdbd` and selected native
`4f0728984`. Production implementation files remain unchanged at this review.

The user explicitly instructed “preserve reference. that is anurag's domain”.
That resolves the previously pending scientific choice without authority to
retune fire/canopy/root behavior. The proposed contract preserves reference
`2e5928702` semantics in specialized lanes and retains selected ordinary physics,
PMET, FC/HK, retention, output formats and executable defaults. It records the
crop-wide specialized `rdmax` exception rather than silently weakening generic
OFE ownership. The ADR correctly distinguishes scientific ownership from
participation in this review.

Protocol reconciliation is explicit and consistent with the handoff: seven-field
soil binding, one restrictive record, existing producer LITTER/BARE order, exact
calendar/OFE agreement, normalized executable date, stale flag retirement and
hydrated string-year fallback. None substitutes a new hydraulic formula. The
contract identifies malformed/absent states and requires retained, visible
failure/superseded artifacts and archive restoration evidence.

## Source checks

I inspected the bound reference `input.for`, `infpar.for`, `grow.for` and the
discovery's full integration inventory against selected source and current
WEPPpy preparation. In particular:

- Reference `input.for:534` reads all seven extension fields and excludes 9005
  from the extra restrictive record. The proposed ownership and units agree.
- Reference `infpar.for:634` uses the distinct `kfs`/`kus` interpolation, minimum
  ground cover, .99 saturation factor and feedback to `ssc(1:2)`; this is not a
  9003 lower-bound extension. The contract preserves actual parenthesization.
- The existing saturation cap at reference `infpar.for:615` precedes the extra
  .99 scaling. For initially saturated inputs the final ratio can be .9801;
  implementations and reference probes must not silently collapse the two steps.
- Reference fire predicates, differing comparison/assignment quantities,
  clamp/log order and crop-type root-depth mutation are all preserved explicitly.
  Missing fire state remains zero; inserting a `fireflg` guard would change the
  chosen reference canopy semantics.
- Isolating reference GROW is preferable to inserting a large set of partially
  guarded changes into ordinary GROW. The `cc_run==0` CO2 branch is unreachable
  when dispatch requires RAP, and the two `hitype` annual blocks occur within
  an `imngmt==2` active-growth branch. Removing those unreachable dependencies
  does not authorize changing any reachable specialized arithmetic.

## Nonblocking clarity note

The decision-preparation artifact still opens with the former unresolved status,
although its final operator-resolution section clearly supersedes that history.
Before the ancestor commit, update its opening status or mark the original
sections historical so a reader sees the accepted resolution immediately.
This is presentation drift, not missing operator authority.

## Implementation and acceptance obligations

The contract is sufficiently concrete to implement; it does not establish that
the port is correct. Final correctness review must verify:

- exact reference comparison on actual compiled dynamic consumers, including
  saturation boundary, canopy-increase branches, fire anniversary, root sharing,
  senescence, initialization/cutting LAI and invalid logarithm domain;
- `ccmxfr` initialization before `INITGR`, which occurs before the proposed cover
  load, plus reset and allocation ownership across successive hillslopes;
- real soil/cover reads for numeric OFEs 2/10 and unequal layers, exact row/token
  counts, calendar parsing, absent/populated flags and date clearing;
- all three GROW callers and required management/residue integration, without
  unrelated reference cutting, CO2, ordinary growth or output changes;
- actual writer/failure/archive restoration and complete canonical preparation
  under the normal service identity, with every enabled companion consumed;
- observer neutrality, ordinary controls, exact final matched pair, fresh native
  and WEPPpy gates, installed interchange/report readback and honest numerical
  limitation disclosure.

The scoped scientific exception does not justify claims of unrestricted
heterogeneous correctness, independent root parameters, calibration or full
conservation. Dedicated security review remains necessary for parsing and
artifact lifecycle changes. Standalone checkpoint ancestors in both repositories
must precede production edits; this review alone does not satisfy the second
independent review requirement.
