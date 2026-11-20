# Fork destination page security review

Reviewer: independent security reviewer. The core route was accepted at
2026-11-20 20:48 UTC and the live dashboard entry at 20:59 UTC.
No medium or high finding remains for the matching-root implementation.

The existing run entry authorizes both before and, for a reserved destination,
after reading the reservation. It validates the exact receipt, destination
pointer, and RQ attempt before showing details. It independently authorizes the
source before linking to it. The final receipt read also covers normal renders
that raced a new reservation. The incomplete view reads no project controller
and skips query target resolution. Protected PUP and Roads results requests
show status until the fork is ready. The configured Query Engine target retains
its existing origin, session, and fork admission controls. The separate WEPP
Reports route uses the existing query admission decision for its link. An Omni
child report may retain a dashboard link while its parent is protected. The
query API still enforces the parent restriction.

The cookie change handles the exact expected 409 conflict on an independently
authorized HTML response. It sends no query token or session marker on that
path. Existing submitted credentials still encounter the query guard.
Backend failures and other response errors keep their existing handling.

The reviewer rejected using a retained failed-child ID as copy evidence after
the RQ root expires. A replacement reservation preserves the previous hash
field. This candidate uses the matching finished job to confirm copy completion,
and yields a generic status-only page when that evidence has aged out.
