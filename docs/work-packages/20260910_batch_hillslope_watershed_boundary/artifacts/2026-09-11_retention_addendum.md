# Prerequisite identity retention clarification

The new downstream gate requires exact root and hillslope RQ identity records.
Production workers previously defaulted successful retention to one week;
SimpleWorker defaults to 500 seconds. Queue delay is unbounded, so either expiry
can reject a valid delayed watershed task. Missing-record fallbacks are rejected.

Clarify the approved durable handoff contract: successful root and hillslope
identity jobs remain non-expiring until explicit operator cleanup. Only these
prerequisite records change retention; terminal watershed/finalizer retention
and unrelated jobs remain unchanged. This is required for the authorized exact
attempt handoff/retry behavior and introduces no deletion mechanism. Operators
must account for retained root/hillslope records when planning explicit cleanup.

Independent read-only approvals on 2026-09-11:

- `/root/contract_correctness`: approve standalone prerequisite amendment;
  prevents normal expiry from invalidating valid delayed proof.
- `/root/contract_security`: approve root/hillslope scope only; test actual RQ
  TTL and preserve strict lineage, without missing-record fallback.

Disposition: both approved, no unresolved high/medium contract findings.
Production TTL changes are withheld until this standalone addendum commit.
