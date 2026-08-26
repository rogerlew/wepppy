# Study Design Amendment: Local Census Fast Path

**Accepted**: 2026-08-09

**Decision owner**: requesting operator

**Scope**: Phase 2 Topanga census and subsequent cross-site screening

## Decision

Cull watershed routing from the candidate-census critical path. The census
will execute full-history hillslope observer runs, outer-join baseline and
mutation events, screen local responses, and adjudicate candidates with
adaptive bracketing and frozen-event replay. It will not run the watershed
binary for every mutation.

The completed Phase 2A routing results remain valid evidence. Criteria 5–7
remain failed under the original pilot design; they are retired as
authorization gates for the local census, not relabeled as passing.

## Rationale

Per-mutation watershed routing projects to 261.7 GB of raw output and about
46.1 sequential compute hours. The hillslope-only census projects to about
4,661 sequential seconds (`1.3` hours), roughly 36 times less model runtime
before parallelism, while avoiding all-channel output retention. The pilot
also exposed unresolved off-path coupling and incompatible interval/daily
volume authorities. Those defects do not prevent measurement of the local
hillslope peak-flow discontinuity that motivates the study. Removing routing
makes the census faster and keeps its claim aligned with evidence the current
implementation can support.

## Amended Census Contract

The local census requires:

1. immutable scenario, build, selection, and mutation manifests;
2. complete antecedent histories and exactly one realized input mutation;
3. outer-joined event ledgers that distinguish absence from zero;
4. preregistered screening floors and candidate rules;
5. terminal dispositions for every requested trial; and
6. adaptive bracketing, frozen-event replay, and mechanism classification for
   selected candidates.

Retain target hillslope pass output and compact observer/event evidence. Do
not retain all-channel output or generate routing hydrographs during the
census.

## Claim Boundary

The amended study may estimate the frequency, magnitude, covariates, and local
mechanisms of hillslope peak-flow discontinuities. It may not claim that a
local response is attenuated, preserved, synchronized, or amplified at a
channel or watershed outlet. Any downstream-impact study is a separate,
sampled follow-up with its own routing authority and acceptance criteria.

## Historical Evidence

The original [Phase 2A exit report](phase2a-exit-report.md) and its routing
artifacts remain immutable pilot evidence. This amendment supersedes only the
decision that all ten pilot criteria must pass before the local census begins.
