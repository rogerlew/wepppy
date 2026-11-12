# Parser candidate and real collector readback

Clean parser candidate `sha256:05f4d047b5460e0a867876aeff6af27b5515afab1a54b31b6b4a5df6d31931a9`
is bound to source `6c0c213a262d1ed89de8bdfa4941b5caf00cb0fa`.
The frozen producer `f86084dea` completed collection in 915.07 seconds, exit zero.
Private bundle: `evidence/parser-batch-20261112/collector-frozen-5/bundle`.
Manifest SHA-256: `c5ed0e97c7818e357aa370de6a67fc2b4db595c006d34abcfe09f7dfcb866823`.

Independent readback reconciles all 702 Python metadata locations, 432 Debian
packages, 3,421 native paths and 1,316 available SBOM executable hashes.
All 15,574 scientific files match the approved manifest. npm covers all 490
lock packages and reports 19 findings. Grype retains 3,016 matches and 330
ignored matches; pyasn1, msgpack and nbconvert have no remaining rows.
There are still 2,105 executable ownership gaps. This is not policy clearance.

Actual parser boundary probes pass, including contained nbconvert output writes,
normal output content and the Msgpack repeated-failure memory regression.
The actual PATH-CE Quarto report test passes once with zero skips in 208.02s;
retained HTML and CSV hashes are respectively
`057af83ff2520b8f609aa0eb86bd0e454a9c31ba68a29720ab259dc7d78af49b` and
`2aaab2616424346ce90f9a418433d0a1990d570e16926f3247050197bd65f6b3`.

The frozen receipt incorrectly classifies Grype's qualified no-function-symbol
warning as an analysis failure. Scanner evaluation section 9 explicitly retains
this conservative module-level finding universe. The bounded producer correction
recognizes the complete warning only with the qualified effective scope hashes
and pinned binaries; it retains the raw warning and a separate reason. Unknown
warnings/errors remain blocking. Fourteen focused producer tests pass in 8.60s.
The original bundle is immutable; a new producer run is required.

The independent audit also finds 135 Grype rows across 24 artifact IDs with
reordered, otherwise identical complete location objects. The evaluator now
compares their complete-object multisets, retaining every field and duplicate
count. Name/version/type and artifact ID remain exact; advisory approval keys
are unchanged. Altered paths, layers, access paths, annotations, missing/extra
locations and duplicate-count changes remain errors. This resolves an order-only
compatibility defect, not a finding or inventory exception.
All 50 evaluator tests pass in 73.36s, including eight new location comparison
cases. Independent security review approves the correction. The full frozen-5
audit is retained privately with SHA-256
`765127a728ca60c33f00d58bbc03cb3d8e37fd45c4d7be7499c40860c1a98af3`.

The native reachability review packet SHA-256 is
`cb93662df24136738fe0c220d3fa2b42978f3dc4aa165ee2a553346d7b420e36`.
It supports further investigation of a narrow MariaDB ordinary-runtime scope,
but does not clear the affected shared/static libraries or general scripting.
Pillow/FreeType and PyCurl/libcurl carry separate Brotli copies; ordinary PATH
rendering does not establish image-wide non-reachability. Repair or explicit
policy-compliant disposition remains required. No exception was approved.
