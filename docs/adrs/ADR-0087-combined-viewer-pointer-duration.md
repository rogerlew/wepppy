# ADR-0087: Combined Viewer Pointer Duration

Status: Accepted for forest implementation
Date: 2026-10-12

## Context and decision

The combined watershed viewer uses Deck.gl's default click recognizer, which
allows 250 ms between press and release. During actual forest acceptance,
software-GPU picking blocked the browser for approximately 2.5 seconds.
Mjolnir measures wall-clock processing time, so even native events separated
by less than one millisecond failed to select a visible polygon.

Set only this viewer's `eventRecognizerOptions.click.time` to 5000 ms at Deck
construction. Preserve pointer count, distance, pan, and double-click settings.
Other map-controller callers do not pass this option and keep their defaults.
This changes stationary press/release recognition only; no scientific formula,
model input, numerical result, unit conversion, or display range changes.

## Decision provenance

- Venue: user/Codex forest implementation conversation, 2026-10-12,
  America/Los_Angeles; exact message time not retained.
- Participants: requesting operator, Codex implementation agent, independent
  correctness reviewer.
- Decision owner and implementer: Codex, as a bounded implementation choice
  under the operator's authorization to complete forest work. The operator did
  not separately request this numeric gesture setting.
- Reviewer: `contract_correctness`, approving the finite setting after checking
  Deck/Mjolnir source and the observed event timing.

## Rationale and alternatives

Five seconds accommodates the measured delay while retaining a finite limit.
An unlimited duration would accept arbitrarily long stationary holds. Async
picking still measured over two seconds on the software renderer. Replacing
Deck's event handling with custom DOM clicks would duplicate picking and drag
logic. A test-only adjustment would leave slow real browsers unable to select.

## Evidence, risks, and rollback

[Picking diagnosis](../work-packages/20261012_portland_combined_viewer/artifacts/evidence/pointer-diagnosis.json)
and the package's final browser audit record direct polygon picking, unchanged
selection after dragging, pan/zoom, and share state. Stationary holds up to five
seconds now select; picking stalls beyond five seconds can still fail. The
keyboard hillslope selector remains available. Remove the scoped option if
pointer semantics regress, and repeat real click and drag acceptance.
