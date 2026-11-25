# Roads retry recovery

## Progress

Contract checkpoint 92770cf9d accepted by correctness and security reviewers. Implemented browser backoff and structured retry eligibility. Focused validation underway.

## Surprises & Discoveries

The observed local timeout consumed 20 seconds of a 25-second server budget and was terminal.

## Decision Log

Wait between completed requests in the browser so a busy public service has time to recover without occupying a worker. Keep existing clients compatible.

## Outcomes & Retrospective

Verify actual upstream count, deadline handling and real Fetch output before delivery.
