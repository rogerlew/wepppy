# Atlas snapshot publication review

Checkpoint `b69fa6e4c`. Independent security and correctness reviewers
identified two risks: logs spanning multiple project directories and an
early visibility check during log parsing. The compiler retains the set of
contributing directories and checks every directory with the existing
NoDb public marker predicate during location row construction. Regressions
cover mixed and all-public duplicate IDs and a marker removal during the
build. Private projects still participate in internal statistics.

The compiler and both landing route suites passed (55 tests). Isolated
Forest application verification used a generated two-project snapshot,
real filesystem markers and two successive compiler generations. All four
JSON aliases and the rendered preview exposed only the public fixture for
both session states. After revocation and recompilation, each returned an
empty Atlas. The removed static snapshot URL returned 404 in the candidate
Flask app. Shared Caddy and the scheduled publisher will pick up the change
through normal deployment. Their post-deployment outputs remain unverified.
