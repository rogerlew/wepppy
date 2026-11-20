# GL catalog readiness

GL-CATALOG-01 implemented and locally validated.

Before sending SQL requests, GL checks catalog readiness through the
[Query Engine HTTP handshake](../../schemas/query-engine-http-access-contract.md#gl-catalog-readiness-handshake).
A tab shares one preparation check and one status poll sequence among all
standard-dashboard queries for the selected run or scenario. Base and
comparison targets can proceed independently.

The basemap, navigation and independent layers remain usable. While a target
prepares, the Layers panel announces “Preparing watershed results…” in a status
region. When ready, GL sends the waiting result queries automatically. A
preparing response to a query returns the target to the same wait. An exhausted
wait or an unavailable response shows a visible explanation and a Retry action.
Retry checks readiness again and reloads affected results. Missing optional
results retain their existing behavior.

Status polling respects the server interval and a finite wait budget. A replaced
scenario or closed dashboard drops superseded waits and does not apply late
responses. Existing flow-duration provenance and Roads availability rules still
govern their respective views.
