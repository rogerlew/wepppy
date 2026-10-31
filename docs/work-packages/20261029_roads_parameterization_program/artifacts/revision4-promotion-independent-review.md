# Independent revision 4 promotion review

**Accepted for exact-byte promotion. No remaining blocker.** This review covers
the prepared sidecars and preflight metadata, not the subsequent installation.

The accepted watershed/hillslope binaries match the scientific acceptance and
preflight exactly:

- Watershed: `2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48`.
- Hillslope: `9ef6b62677407a66255a2b95becc9f350c87ef8e4cf67ab4e543ddb89ed4a010`.

Prepared sidecar SHA-256 values reviewed:

- `wepp_261029.json`: `162756de2f43428f53149c5d6703eb7224be9911d3a4fcd69a615ca07cd80c83`.
- `wepp_261029_hill.json`: `719868551b78678dffc7d525709253541e4238e8684a0e74fe4191fd7da4115d`.

Independently compared all **489** retained build inputs against their frozen
build copies, current working files, and Git blobs at
`b01a739957bef5aacf35b4a89bc13eddc9d94804`: zero mismatches. The current branch
matches `origin/HEAD` (`wepp_260430_negmeltfix_comparator`); the recorded build
base is an ancestor. Metadata explicitly records that the research build
preceded the source commit, uses executable mtime rather than promotion time,
and does not claim a fresh clean-checkout rebuild.

The retained builder pins `/usr/bin:/bin`; build logs show the declared system
compiler and flags. All five declared tool hashes match the system tools.
Candidate source-manifest/build-log hashes, every linked sidecar evidence hash,
all **25** scientific acceptance evidence hashes, and prior binary/sidecar
identities match. The newly retained artifact-policy receipt reports exit zero;
its log bytes and both sidecar references were independently checked.

Both sidecars preserve revision 3's feature, capacity, execution-calendar,
paired-interchange, and math-runtime contracts exactly. Validation counts
(1,253 native, 28 watchlist, 99 Disturbed, 840 Roads, 348 downstream, 1,188
observer replays, 864 Cedar hillslopes/24 years) agree with accepted evidence.
Roads magnitude nonacceptance, the two explained fraction flags, and the
40,006 bounded negative-capacity observations remain disclosed.

Residual scope: promotion must preserve these exact executable bytes; rebuilding
or stripping would invalidate this exact-pair review. Post-vendor provenance,
application checks, and publication/delivery tracking remain separate. This
review does not authorize a default change, Windows release, or deployment and
does not rerun already completed scientific/model gates.

Machine receipt: `/tmp/revision4-promotion-independent-review.json`.
