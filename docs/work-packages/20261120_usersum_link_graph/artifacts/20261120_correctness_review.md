# Usersum correctness review

The independent reviewer confirmed local vendor traversal and fragment
checks on real Git fixture repositories. They reproduced the regression
in the historical release-note URL after the initial rebuild and found
that the archive refresh removed a WEPPpy-specific withdrawal notice.
The archive checkpoint pins an authoritative upstream commit and
preserves the registered historical brief. Usersum shows the withdrawal
guidance in the rendered 260727 release notes while raw Markdown remains
byte-for-byte upstream content.

The reviewer independently verified all five historical seeds against
their archive Git blobs and ran ten passing focused tests. The final
isolated run passed 123 tests, including the restored historical routes,
both copied IFOLP links, the withdrawal notice, exact fragment matching,
and strict source mode. Its worktree receipt is
`.wctl-test-runs/3ff0b025dc9848b2882d385014d0c99a/receipt.json`.

The real build produced 5 WBT, 88 WEPP Forest, and 1 Roads page. Direct
readback verified all 94 against the matching committed blob. Heading
lint, executed with the two production pins in a clean Python environment,
reported one unresolved link from the WEPP Forest rock-water incident
to a WEPPpy artifact that does not exist in the checked-out source.
