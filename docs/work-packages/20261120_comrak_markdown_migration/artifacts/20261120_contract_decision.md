# Comrak migration contract checkpoint

The operator explicitly authorized complete cmarkgfm replacement and a
Python extension scaffold. The starting revision is `547ada295` on
the earlier Usersum feature branch. The canonical Markdown rendering
contract covers the adapter, profiles, untrusted Markdown, parsed links,
published heading IDs and consumer compatibility. The existing Usersum,
Browse filesystem and web runtime contracts remain applicable.

This change replaces existing parser plumbing and adds opt-in trusted
Python extension selection. It has no data schema migration. Formatter
differences require corpus evidence, especially ordered lists, code fences,
task lists, links and heading IDs. Empty and malformed inputs must retain
each caller's expected behavior. README preview and Browse handle
user-influenced data. Raw HTML and unsafe URLs must stay suppressed.
Links from code and image descriptions must not become vendor edges.
Use direct renderer and route tests plus the real vendor graph and docs lint.
The application image must prove dependency installation and affected
workflows before rollout.

The independent correctness review found no blocking compatibility issue
in the contract. Its separate 152-page check matched published IDs and
link destinations in both Comrak rendering modes. The implementation
will register the shared adapter in both Docs Quality path filters and
test relative references, fragments, labels, titles, code and images.

The independent security review found that a general AST hook could
introduce native Raw nodes even with source HTML disabled. The contract
now requires private safe render options, a destination-only callback,
and direct rendering for user-controlled Browse and README inputs.
Verify both render paths, the wheel SBOM, and removal of cmarkgfm and
the import-colliding plain binding from the candidate runtime.
