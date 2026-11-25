# Roads retry recovery

## Progress

Contract amendment drafted. Independent reviews, implementation and validation pending.

## Surprises & Discoveries

The observed local timeout consumed 20 seconds of a 25-second server budget and was terminal.

## Decision Log

Wait between completed requests in the browser so a busy public service has time to recover without occupying a worker. Keep existing clients compatible.

## Outcomes & Retrospective

Verify actual upstream count, deadline handling and real Fetch output before delivery.
