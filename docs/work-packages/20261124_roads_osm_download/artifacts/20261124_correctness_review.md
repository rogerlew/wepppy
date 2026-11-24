# Correctness and usability review

Reviewed on 2026-11-24 UTC by independent correctness and UX reviewers on docs/osm-roads-download against the [canonical contract](../../../schemas/roads-osm-download-contract.md). The separate security review covers trust boundaries.

| Project or response state | Direct check and disposition |
| --- | --- |
| Enabled, never uploaded | Download succeeds without creating roads.nodb. Review found bootstrap reads and later model actions required missing state. The component now reveals those actions after the first successful upload. Actual multipart publication initializes the controller and detached readback confirms field mapping. |
| Existing project/input | Download retrieves separate geometry. Edited uploaded data stays active until the user uploads a replacement. Existing upload/prepare handler coverage retained. |
| Empty map result | Chromium exercised an empty collection after a successful keyboard download. Inline feedback identifies missing mapped roads and points to upload. |
| Missing or oversized extent | Validation rejects the request before contacting Overpass. The user can supply an inventory. |
| Malformed upstream data or upstream outage | Explicit failure without replacing project data. The default public interpreter reported capacity errors in live checks. |
| Private, multisegment, missing tags | Loopback HTTP response and GeoJSON tests cover private roads, clipping, unknown surface, arbitrary tag names and independently editable model attributes. |
| Read-only and insufficient role | Disabled action and explanation. The route checks the feature decision before acquisition. |
| Restored input | Normal Roads upload stores the edited source as before. Acquisition itself produces a browser download and adds no archive member. |

The UX reviewer first traced the existing Roads upload/status and Pure button-row patterns. They inspected the rendered [desktop](desktop.png), [phone](phone.png), [read-only](readonly.png) and [empty-result](empty.png) views. The revised introduction identifies both starting options. Help, format, button and next step appear together, without a new modal or custom CSS. Browser readback verified no horizontal overflow at 390 CSS pixels and a keyboard-initiated file download with the expected name and contents. Captures use the candidate Jinja control with application styles and fixture run context. The review was an expert walkthrough.

Correctness reviewer accepted the final absent-controller behavior, actual multipart round trip and preservation of the existing Mods menu. No outstanding feature correctness or usability findings.

The publication check identified two Roads source fingerprints for independent review. The constants change shares the existing upload cap. The new export module supplies GIS features to the download route. The reviewer compared the current source hashes with the original published hashes and confirmed the register accounts for both changes. The October full-project routing results retain their dated stale notice and the limitation covering five skipped connected segments.
