# Run-page Features Export presentation refactor

Opened 2026-11-24 UTC. The run page assembles the export control from catalog definitions, local output schemas and published profiles. Move this presentation logic out of the Flask blueprint so a maintainer can trace the browser payload without traversing unrelated request handlers.

The complexity budget is two sibling Python modules and the existing runtime dependencies. Security impact is low. The route continues to own access checks and calls export presentation only inside its existing feature gate. The extraction changes no authorization, filesystem policy, configuration or deployment boundary.

Acceptance requires identical helper logic, route wiring, passing focused payload and template tests, a broad pytest attempt and local-only integration. See the [tracker](tracker.md).
