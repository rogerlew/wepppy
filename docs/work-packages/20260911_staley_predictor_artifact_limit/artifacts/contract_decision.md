# Contract decision

Base: 7447e6243 plus the uncommitted completed upload/status and themed legend
repairs, which are preserved. User reported run_m1_rq resource_limit and authorized
repair by requesting investigation of the failing model workflow.

Exact delta to docs/rainfall_results.md: distinguish fixed upstream terrain
artifacts from rainfall inputs. Use the operator-selected 96 MiB cap for the three
allowlisted TIFFs; keep summary/manifest at 1 MiB and rainfall/parquet admission
unchanged. The operator explicitly selected 96 MiB for these generated predictor rasters.

The generated slope raster is 74,129,489 bytes; terrain preparation and its
10-million-cell boundary already succeeded. Hashing is streamed; no additional
raster decoding or allocation is introduced. Keep fixed artifact names, parent
symlink checks, exact hashes and final publication checks. No schema mutation,
model coefficients, scientific threshold, unit conversion or heuristic change.

Compatibility: accept previously rejected valid terrain output, reject TIFFs over
the terrain cap and retain smaller rainfall limits. Test a >64 MiB pinned TIFF,
oversize TIFF rejection, unchanged rainfall cap and hash mismatch. Rerun the
user's project through the existing run button and verify completed publication.

Reviews/disposition: pending. No runtime change before checkpoint commit.

Operator refinement: “add margin to this. 96 MiB”. This supersedes the initial
512 MiB proposal. Initial hash and final consumed-file recheck both use this
explicit artifact-only cap; JSON/rainfall caps remain unchanged. No ADR required:
this is a file-admission resource bound, not model parameterization.

## Independent reviews

contract_correctness and contract_security independently accepted the revised
96 MiB boundary before implementation. Both identified that digest() and final
recheck() also enforce the default cap; disposition: register explicit per-file
limits only after successful fixed-artifact hash validation and carry them into
final recheck, without changing consumed hashes or widening rainfall admission.
No blocking contract findings remain.
