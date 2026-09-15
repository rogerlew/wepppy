# Runtime completion compatibility and regression plan

Authority: scientific checkpoint `89d673c38`, generic source checkpoint
`7328a0004`, replay checkpoint `0792c7e59`, acquisition approval `2de5ca737`.

Changes remain additive. Preserve the M1-specific local result entry point and
all v1 tables/columns/defaults; introduce shared explicit-model dispatch, with
M1/M3 identity cross-checking on readback. Version-2 predictors add only recorded
coverage and the exact mask to results; old results require neither. Verify
event/design/inverse numbers against the existing independent scalar engine,
including unavailable predictors, missing rainfall and zero support. Archive
readback must use retained result artifacts, never provenance-directed paths.

Source acquisition produces fresh module-owned receipts. It neither activates
them implicitly nor modifies Soils caches/build outputs. Test endpoint/range/
identity/time/byte controls, malformed sources, native encoding and WAL drift
before live acquisition. Initial scope is the approved development basin; use
distinct basin fixtures to prove parameterized keys and windows.

For subsequent worker wiring, bind source receipts to authoritative project
selections, preserve existing locks/accepted pointers and validate generated
result files, browser/downloads and archive restoration. Compare upstream soil
and propagated WEPP input hashes before/after; new reader errors must not mutate
them. Retain failure attempts and previous accepted results. Full-suite and
focused results will be appended as each stage actually completes.
