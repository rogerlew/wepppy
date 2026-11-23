# Watershed atlas

The [publication decision](artifacts/20261123_contract_decision.md) and canonical
Run Atlas contract were reviewed and committed in `51f9a7aeb` before implementation.
The [implementation security review](artifacts/security_review.md) passed.

All 53 compiler and landing route tests passed on the candidate. A Chromium
fixture rendered a watershed and verified its four-line hover tooltip with
local Deck.gl and MapLibre assets and an empty test basemap. Full pytest
preflight stopped on missing browser manifests, native parsers and comrak
in the isolated runtime. Production rollout and snapshot regeneration are pending.
