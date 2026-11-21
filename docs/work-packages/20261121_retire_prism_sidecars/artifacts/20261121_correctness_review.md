# Correctness and validation

An independent reviewer verified both native and Python changes. Direct native execution with four daily rows and two inversions produced the expected floored weather and only the revised CLI. Dedicated sidecar retention tests were removed, including the archive fixture written for their retention. Generic browse/archive behavior and tests remain in place.

Absent and populated climate directories follow existing staged publication. CLI, raw source data and EDDE companion metadata keep their established meanings. Invalid calendars, nonfinite forcing and invalid source temperatures still raise errors. The real NoDb tests exercised published mappings and failed revision readiness.

The paired py312 native build at c42f58f7d1e3b62b9d2e97da9d9509dd80e31bb5 passed 23 crate tests. Six isolated WEPPpy test modules passed 130 tests, receipt d6bfb02ddc304890a72af68487978f78. Replayed the retained diagonal-intersection sample from centroid weather, 16,436 raw daily PRISM dew points and six source/target monthly normal arrays. The fresh directory contained only _142702.cli, SHA-256 2f8092cb3a33bff1d06cb021f43aea115fefbda8f518b0e5627f474834b95b26, byte-identical to the production CLI. Production rollout and historical cleanup are separate operations.
