# Usersum vendor link graph and heading lint

Usersum should open documents linked from vendored guides and report broken
targets during the documentation build. Authors should be able to check
fragments against the IDs that Usersum publishes.

The scope is the Usersum vendor build, Markdown link resolution, and Docs
Quality checks. The operator approved recursive publication of reachable
committed Markdown and heading normalization in the 2026-11-20 conversation.
The complexity budget is the existing parser, Git plumbing, the documentation
build, and the current web service. A parser replacement requires separate
dependency and rendering parity evidence.

Security impact is high because vendoring publishes additional files. The
security review checks commit provenance, symlinks, path boundaries, and
manifest access. Acceptance requires reading generated files and following
rendered links through Usersum as well as checking the build diagnostics.

Local implementation and focused acceptance are complete. The feature
branch retains both reviews and the original source commits for generated
content. The broad runtime gate and integration remain open.
