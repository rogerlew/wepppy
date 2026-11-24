# GL dashboard sidebar renderer

Faithfully extract the responsibilities of the sidebar renderer and consolidate its duplicate WEPP channel controls. The dashboard contract lives in [the UI guide](../../ui-docs/gl-dashboard.md). Acceptance requires rendered sidebar and legend evidence through the existing factory, including both channel families. Security impact is low. The change uses existing UI callbacks and introduces no new data or execution boundary.

Local implementation accepted on 2026-11-23 UTC. See the [execution and validation tracker](tracker.md).
