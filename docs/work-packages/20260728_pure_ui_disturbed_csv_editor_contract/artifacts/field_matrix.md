# SURF-10 Disturbed CSV Editor Contract Matrix

| Boundary | Required behavior | Evidence |
| --- | --- | --- |
| Render | escaped run/config, producer URLs, CSRF, accessible status/actions | actual Jinja render |
| Initialize | session authorization precedes atomic snapshot load | executable inline Jest |
| Runtime dependency | missing spreadsheet CDN runtime is visible; save stays disabled | executable inline Jest |
| Save | nonblank rows plus loaded SHA-256; CSRF; one in-flight mutation | executable inline Jest + routes |
| Concurrency | stale poll/save locks editing and exposes recovery | executable inline Jest + routes |
| Recovery | failed stale reload retains lock and recovery action | executable inline Jest |
| Variant | base/extended identity is stable across render/read/write | disturbed route tests |
| Persistence | authorized, locked, validated, atomic, fingerprinted write | route + NoDb lookup tests |
| Shared producer | Geneva supplies the same config contract for its CN table | Geneva route tests |
