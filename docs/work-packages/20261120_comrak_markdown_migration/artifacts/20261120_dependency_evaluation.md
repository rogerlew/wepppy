# Markdown parser dependency evaluation

The dependency precedent registry contains no prior Comrak adoption. The
existing cmarkgfm pin supplies all active Markdown rendering. Comrak
overlaps that baseline and adds parsed link access and Python extension
options. Mistune is installed for other consumers and does not supply
the requested Comrak interface. A new Rust wrapper or service would
add a build and release workflow without a capability advantage here.

PyPI `comrak` 0.0.16 packages Rust Comrak 0.54.0. That crate is in the
affected range of the [autolink advisory](https://github.com/kivikakk/comrak/security/advisories/GHSA-xg9p-p4jc-c46g)
and the [table rendering advisory](https://github.com/kivikakk/comrak/security/advisories/GHSA-j7hq-qg5v-47jq).
PyPI `comrak-ext` 0.2.8 packages Rust Comrak 0.59.0, beyond both fixed
versions. Its source distribution Cargo lock contains 117 entries,
including build, optional and platform-specific packages. The Linux
x86-64 CPython 3.12 wheel embeds a CycloneDX inventory with 110 listed
components. It names Comrak 0.59.0 and PyO3 0.30.1. The PyPI SHA-256
for this wheel is
`b7a307f9aa87ffe0dda8a0235364cbd3a8e421503b935c6320d2407aebb7a876`.
The ARM64 CPython 3.12 wheel has SHA-256
`0ee5827a0995eacebdc0247c0610d5a6aa3775f04a3e725b15c7096f8ead2d14`. Base wheel
installation has no Python dependencies. PyPI publishes CPython 3.12
manylinux x86-64 and ARM64 wheels. The installed wheel includes Python
type declarations. Its public module name is `comrak`. Do not install
both distributions in the same environment.

The Rust library has an active release and advisory process. Both
Python bindings are independently maintained. The reviewed wrapper
release is still pre-1.0 and exposes a native data model. Keep that
model behind one adapter and compare semantic output at upgrades.
Package funding and maintainer continuity were not established.

In an isolated Python 3.12 environment, rendering the 152 UTF-8 Markdown
files under Usersum took 61 ms per corpus with the old pin, 34 ms with
direct Comrak render, and 116 ms through the Python AST round trip.
These are means of three passes on the development host and exclude
HTTP, disk reads and link resolution. A separate HTML-parser comparison
found identical sequences of published heading IDs and link destinations,
and identical tag counts on each page after applying the existing heading
normalizer to both outputs. This is compatibility evidence, not a live
latency claim. Use direct rendering for paths that do not need the AST
and test the actual application workflow before rollout.

Candidate outcome is conditional on direct route validation and
installation and provenance evidence for the platform wheel.
