# ADR-0028: GridMET Download Retry and Concurrency Bounds

Status: Accepted

Date: 2026-08-31

## Context

A production watershed build issued 376 annual GridMET NCSS requests with 12
workers. THREDDS returned 36 HTML 502/503 responses, which the client published
as `.nc` files. Single-location requests already attempt three requests with
5- and 10-second delays but have no timeout or response-schema contract.

## Decision

Use at most three attempts per GridMET request. Retry transport timeouts and
HTTP 408, 429, 500, 502, 503, and 504 responses, plus HTTP-200 payloads that
fail the expected JSON or classic NetCDF3 validation. The gridded NCSS request
uses `accept=netcdf`, so classic NetCDF3 is the explicit wire-format contract;
the client rejects structurally incomplete files before semantic validation.
Delay 5 seconds before the second
attempt and 10 seconds before the third. Use a 10-second connection timeout and
120-second read timeout for grids, and a 10-second connection plus 60-second
read timeout for single-location JSON. Limit gridded variable/year acquisition
to four concurrent workers. Reject single-location responses larger than 32
MiB and gridded responses larger than 512 MiB, counting streamed bytes even
when `Content-Length` is absent or compression is used. Reject redirects.
For single-location JSON, require exactly one record whose date axis is the
complete, ordered daily range requested by the caller, including leap days;
all required numeric series must have the same length.

For a grid, require the requested variable with `description` and `units`, the
`day`, `lat`, and `lon` coordinates, the exact `(day, lat, lon)` dimension
order, no more than one calendar year, and spatial dimensions bounded by the
requested box at GridMET's 1/24-degree resolution with four cells of alignment
allowance. Completed years require 365 or 366 days; the current year may be a
nonempty published prefix.

Permanent HTTP client errors fail on the first response. No attempt may publish
before validation.

## Decision Provenance

Decision Venue: WEPPcloud operator conversation and production incident triage,
2026-08-26 through 2026-08-31

Participants Present: WEPPcloud operator, Codex

Decision Owner(s): WEPPcloud operator

Implementer(s): Codex

## Rationale

Three attempts and the existing 5/10-second schedule preserve the established
single-location retry budget. Four concurrent grid requests reduce the observed
12-request burst while retaining parallelism across a long annual matrix.
Separate read timeouts reflect the larger gridded payload. Validation retries
cover proxies that return HTML with either an error status or HTTP 200.
The 32 MiB JSON ceiling is far above a multi-decade, eight-series single-point
response. The 512 MiB grid ceiling is above observed watershed annual subsets
while preventing an upstream response from consuming unbounded run storage.

## Alternatives Considered

1. Keep 12 workers and add retries: rejected because synchronized retry can
   increase pressure on an already failing upstream.
2. Serialize all requests: rejected because 376 annual products would make
   ordinary builds unnecessarily slow.
3. Add indefinite retry: rejected because jobs need bounded failure and useful
   operator feedback.
4. Switch to aggregated grids or a shared cache: deferred to a separate
   evaluation requiring parity, storage, and performance evidence.

## Consequences

Transient failures may add at most 15 seconds of deliberate backoff per
request, plus bounded network timeouts. Large watershed builds issue fewer
simultaneous requests and may take longer when the upstream is healthy. They
will no longer proceed with corrupt final artifacts.

## Evidence and Review

- Production run `mdobre-massive-delusion`: 340 valid and 36 invalid annual
  artifacts; invalid payloads were 11 HTTP 502 and 25 HTTP 503 HTML pages.
- Focused automated and Forest1 evidence will be recorded in the associated
  work package.

## Rollback

Concurrency may be restored only through an ADR update backed by upstream-load
and build-duration evidence. Do not roll back atomic publication or payload
validation; those are correctness requirements, not tuning knobs.
