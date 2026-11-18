# Integration validation

Runtime implementation: `c433c6ee3`; final image/source identity is retained in
image-validation.json and image-native-provenance.json. Local native identity is
separately retained in local-native-provenance.json. Both inventories match the
reviewed Rust sources; binary hashes differ by build environment.

213 focused checks, 152 adjacent filter/auth/security checks and 13 native Rust
checks passed. After the first broad run exposed an older file-route test missing
the native dependency fixture, its fixture/header assertions were updated; all
104 file-route checks pass. No production behavior changed in that correction.
The first broad run stopped at 1,032 passed/32 skipped/99 deselected on that test.
Broad rerun remains pending; no package-closeout claim yet.

All 46 real files match legacy bytes, covering 43 observed schema/codec groups
and every affected wide/dictionary file. Source and output hashes, rows, bytes,
child resource metrics and timings are in real-file-parity.json. Boundary checks
include dictionary 131,072/131,073 and columns 128/129, empty and populated.

Final image tests prove eight-worker real HTTP delivery under UID1000:GID993 and
wepp1's configured UID1002:GID130/groups[130], runtime umask022. Two slow readers
hold both slots; a third gets503, disconnect cleans fixed directories, and two
persistent lock files remain. A 444,752,939-byte real CSV matches the oracle hash;
raw bytes remain accessible after malformed/tampered representation failures.
Successful hash/outcome logs are retained. Filtered1/2-row bytes and no-match422
pass with legacy enable0/cap1 settings; CSV policy ignores those non-CSV controls.
Operator umask077 readiness checks separately prove fixture permissions and an
alternate runtime UID; they do not assert runtime umask077.

The image JSON `seconds` field measures body reads after headers, not conversion.
Conversion/CPU/RSS are in correlated service logs. Single local benchmark samples
are not production-capacity estimates. Offline fixture Redis startup warnings do
not constitute production-health evidence. Deployment and target-host auth/secrets,
mount/proxy validation remain separately authorized gates.

Rust formatting, shell syntax, Markdown checks and broad-exception enforcement
pass. Quality telemetry and independent reviews are retained alongside this file.
