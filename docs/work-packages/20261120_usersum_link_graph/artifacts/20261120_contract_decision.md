# Usersum link graph contract checkpoint

The starting implementation is `6fefde151`. The operator requested recursive
vendor traversal and missing-file warnings, approved reachability for committed
source documents, and requested heading normalization in Docs Quality. The
operator directed feature-branch execution with a contract-first work package.

The canonical Usersum specification defines the approved behavior under
**Link Resolution and Prefix Safety** and **Vendor Sync and Authoring Policy**. The
contract-first change standard and generated artifact validation standard apply.
Implementation conformance is pending.

The existing missing copies are an implementation gap. Using committed Git
objects and adding normalizations to quality checks are intentional contract
changes. Keep the published fragment algorithm because existing URLs use it.
Retain manifest role checks and strict source mode. Continue traversal through
cycles and expected missing targets with deterministic warnings. An invalid
configured ref is a build error because the build cannot identify the intended
source. Test absent and empty sources, existing snapshot updates, transitive
links, reference-style links, fragments, symlinks, working-tree-only files, and
paths escaping a source tree. Verify emitted links and generated document bytes.

## Independent review dispositions

The correctness review found ambiguity around strict source mode and stale
copies. The canonical contract now scopes public reachability to normal
source mode, retains explicitly configured strict mode, and makes default
rebuilds remove stale generated copies. It defines exact decoded fragment
validation and preserves cross-root links with valid runtime targets.
Correct the WBT configured ref to its actual `master` branch. Verify the
write-capable RQ index caller and its read-only scheduler path.

The security review found destination symlink and same-repository role
bypass risks. The canonical contract now requires disjoint destinations
within the vendor root, rejects destination symlinks before mutation, and
requires links to manifest-tracked originals in the self-vendor to keep
their canonical route and role. Git tree and blob reads provide the
committed regular-file boundary. Direct regression tests will exercise
the source, destination, and route boundaries.
