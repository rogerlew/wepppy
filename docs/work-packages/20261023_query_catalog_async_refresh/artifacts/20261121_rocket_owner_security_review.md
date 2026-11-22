# Rocket batch owner admission security review

Reviewed on November 21, 2026 by the independent security reviewer against
`d9e5ba7eb` and the Rocket admission working diff. Security impact is high
because this changes shared RQ admission. The selector and admission ledger are
operator-owned Redis state. Producer-supplied scope metadata is a separate trust
boundary.

## Findings

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| SEC-01 | Medium | A malformed non-UTF-8 selector can raise through producer notification after the producer has already written its receipt. | Closed. Bounded byte comparisons match configured namespaces. Invalid bytes leave the optional cap inactive and display an explicit diagnosis. |
| SEC-02 | Medium | An active refresh binding can pass ledger validation with a missing or malformed scope. Owner accounting can then throw or silently omit the binding. A non-object scope can also break the admin snapshot. | Closed. Active bindings with unknown scope or invalid target owner paths return an accounting error, retain the receipt and display the accounting diagnosis. |

## Boundary checks

- Enqueue derives owner membership from the freshly resolved project scope.
  The watched ledger and selector fence concurrent admission and rollback.
  Terminal, uncertain cancellation and inventory reservations retain their
  existing execution and global-cap rules.
- The panel is read-only and limited to Admin/Root. Displayed owner labels are
  truncated hashes. They support correlation and provide no secrecy guarantee
  for guessable owner names.
- The scoped regression uses disposable Redis with concurrent peers, a
  preexisting reservation, another owner, cancellation, rollback, durable
  receipts and published catalog entries. Security review inspected the test source.
- An independent Redis process using a fresh private Unix socket exercised
  invalid UTF-8 and an oversized suffix after a valid namespace. The admin
  panel flagged both, and enqueue succeeded with the invalid selector. With a
  valid selector, each of four damaged active scopes (null, list, null relative
  path, parent traversal component) returned the pending accounting error. The
  panel explained the block, ledger bytes and queue length stayed stable, and
  the second project retained its single durable receipt. All checks passed.

## Verdict

Security gate passes with both medium findings closed. The independent check used
only disposable local Redis and project directories. Deployment, namespace to
storage mapping, mixed-host worker continuity and production performance remain
separate operational gates.
