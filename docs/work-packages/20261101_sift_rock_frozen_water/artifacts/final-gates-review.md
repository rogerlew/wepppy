# Additional reader-control review

Disposition: **PASS for the four retained negative controls. Broad-suite final gate remains pending.** The reviewer inspected existing artifacts and did not rerun controls or invoke a native model.

The public `reader-controls.json` is byte-identical to the private control receipt; SHA-256 is `eb3b0e23f164ec702371328d5a3785e88ad79f7d3248dca6ba458410145a4033`. Its reader binding matches `read_sift_outputs_v2.py` SHA-256 `7321e9137ed3c5b4e4b60f0666646c09829775930cc1d4226018cbe210d336fb`.

Inspected the control script and all four mutated files, per-control receipts and stderr. Each exits 1 for its intended reason: numeric stars in a water row, an additional numeric star field inside an otherwise recognized report summary, duplicate daily key, and zero POR causing an invalid SAT denominator. Mutation hashes and rejection messages agree with the public summary. These exercise the actual reader paths, including the narrow decorative-star exception; they are not replacement predicates disconnected from the reader.

Mutations target disposable copied outputs/initialization observations. The script records no native invocation and compares hashes, sizes and modification times for all 100 original history members before and after, asserting equality. The retained receipt reports that check passed. These controls strengthen the reader acceptance evidence without altering any original history or converting prior validation failures into native reruns.

No additional blocking finding. This note supplements, and does not replace, the implementation and packaging reviews. Exact final broad-suite disposition is still required. Reviewer writers are clear after scoped documentation lint.

## Final broad-suite gate closure

Final disposition: **PASS.** Independently verified the completed `wctl run-pytest tests --maxfail=1` receipt against the retained log: exit 0, 12,634 passed, 423 skipped, 5,830 warnings, 3,589.92 seconds. The public `test-results.json` and private `broad-test-result.json` are byte-identical. Actual log SHA-256 is `9648bf53a9e5f2d23aa444c6625f72ef28ee7a713fafe9e6be1b084efed90150`, matching both receipts.

Production SIFT and test-file hashes remain identical to the final implementation review bindings. This closes the broad-suite pending gate recorded above and in the implementation/packaging reviews; no test rerun was performed. No raw evidence was written during this closure. All implementation validation gates reviewed here are complete; deployment and migration remain outside scope. Reviewer writers are clear for freeze/archive after scoped lint.
