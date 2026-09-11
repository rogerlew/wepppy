# Contract reviews

Independent read-only correctness and security reviews accepted. Initial findings
were conflicting hidden/cleanup policies, insufficient worker exclusion, and loss
of failure identity after retry. All were closed before implementation: canonical
domain/readme/local contracts amended, admission/lifecycle and active-job guards
specified, per-attempt receipts/error logs retained. CI uses the existing generator.

Final source/live gates include tamper rejection, interrupted migration recovery,
archive/restore byte equality, and normal browser inspection. No contract blockers.
