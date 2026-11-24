# Security review

Independent security reviewer, 2026-11-24 UTC, branch docs/osm-roads-download. Scope includes the run-scoped route, UI, Overpass client and first upload into an enabled project.

The initial checkpoint was revised to require the existing Roads action decision and CSRF-protected POST for generation. Report inspection preserves its established permissions. The reviewer exercised the role matrix for anonymous, ordinary user, eligible WBT PowerUser, read-only, wrong backend and denied run access. Only eligible actions proceed. Generation takes its extent from Ron and its upstream from deployment configuration. It accepts no caller-provided destination or output path.

The foreground client disables redirects, requests identity encoding, caps the incoming stream at 8 MiB and uses one request inside a total deadline. The export keeps multipart clipped geometry under one way ID and bounds the serialized attachment by the 10 MiB web upload cap. Errors omit upstream payloads. Cached hydroenforcement uses a versioned selection identity so old area features cannot reappear from older tiles.

First upload through the absent-controller state uses feature entitlement and enabled-module checks, a fixed run-local directory, existing geometry validation, evidence retention and transactional publication. The controller uses the saved Ron configuration. Existing-controller admission stays on the established route. Source attributes are data in a GeoJSON attachment. The final disposition records no open medium or high findings.
