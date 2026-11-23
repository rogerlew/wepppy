# Refactor the GL dashboard sidebar renderer

## Purpose and milestones

Dashboard maintainers should be able to follow section assembly, legend editing and channel selection independently. In wepppy/weppcloud/static/js/gl-dashboard/layers/renderer.js keep createLayerRenderer as the public entry point. First capture the existing DOM and callback behavior. Move legend rendering and editing together, extract ordered section construction and RUSLE tolerance handling, and consolidate channel controls while retaining their distinct IDs and asynchronous refresh callbacks.

## Progress

- [x] 2026-11-23 UTC. Identified the renderer entry point, duplicate channel controls and existing DOM tests.
- [ ] Extract and wire the modules.
- [ ] Validate rendered output and review the local integration.

## Surprises & Discoveries

The renderer spans 1,671 lines. Both channel families use one radio group and clear the other families before refreshing data.

## Decision Log

Preserve the existing state readers, render snapshots, event order and raster object references. The dashboard uses native browser imports, so exercise the candidate module graph directly.

## Validation and recovery

Run the renderer-open-state Jest suite from wepppy/weppcloud/static-src. Exercise both channel families with asynchronous callbacks and inspect selection and rerender order. Run frontend lint, Jest and Node suites, browser smoke, and the repository pytest sanity command. Record gate results in the tracker. Revert the local merge with its first parent as mainline if rollback is needed.

## Outcomes & Retrospective

Execution pending.
