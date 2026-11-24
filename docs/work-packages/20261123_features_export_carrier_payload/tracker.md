# Features Export carrier payload tracker

Opened 2026-11-24 UTC from local master at `00c9eb26f`. The previous package
extracted carrier identity and cache validation. This package addresses the
duplicate processing in the service function that consumes the carrier core.

## Local validation on 2026-11-24 UTC

The original service passed all 13 materialization tests, including both new
spatial event cases (receipt `2e8246af7d0e41d9b08c61b08c16e83f`). The
candidate passed all 239 Features Export NoDb, RQ, and route cases (receipt
`47f9391640b249b58b46dd9e8e0adc59`). Both runs used the isolated wctl
Python profile and reported stable source fingerprints.

The event cases read the serialized geometry, EPSG code, feature properties
and materialization metadata. One source key matched and kept its metric.
A missing match retained the geometry and produced a null metric. The tabular
cases exercised the geometry-access guard and read identities from watershed
Parquet. Writer tests opened ZIP members as CSV and Parquet and checked the
row count and provenance columns. The GeoPackage service case queried the
generated SQLite feature table and counted two rows with two geometries.

The carrier builder shrank from 295 to 184 lines. Its spatial attachment
helper is 70 lines. An AST comparison found all 84 other existing service
functions and classes identical. The changed-code exception guard passed.

The broad suite passed preflight and ran with `--failed-first --maxfail=1`.
It stopped at `test_adduser_errors_when_user_unknown`. The team route returns
“WEPPcloud” where the test expects “WeppCloud”. The same assertion failed
on the unmodified local master in a separate invocation. The baseline receipt
is `d47c7ad92b9a4aeb9b6adafbc8f06486` and the candidate broad receipt is
`acb63d0d79cc420a86fe78ea4a74caa5`. Full-suite validation is incomplete.
