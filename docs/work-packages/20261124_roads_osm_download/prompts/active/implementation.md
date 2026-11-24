# Download, edit and upload mapped roads

## Purpose and context

A user can acquire a road map for their project without supplying an input or running a model. The Roads form in wepppy/weppcloud/templates/controls/roads_pure.htm already offers upload and mapping. wepppy/topo/osm_roads/overpass.py resolves OSM way geometry and tags. Use the run map extent and preserve original evidence alongside the fields Roads already recognizes.

## Progress

- [x] 2026-11-24 UTC. Identify upload and secondary button patterns and inspect model resolution.
- [ ] Commit approved contract after two independent reviews.
- [ ] Implement shared road selection, GeoJSON acquisition and integrated download. Amend ENDUSER.md.
- [ ] Verify download, GIS-edit and upload, browser states, screenshots, usability and security review.

## Surprises & Discoveries

The existing importer discovers uppercase design, surface and traffic fields. Raw OSM surface needs its own identity. The tile cache currently keys by highway class and the request path by tile cover, so reusing a mutable tile-cover artifact across distinct project downloads could return another extent.

## Decision Log

2026-11-24 UTC. Use a single read-only export through the existing Overpass client. Independent download is useful even before an analysis upload exists. Preserve arbitrary tags as JSON text for GIS compatibility.

## Plan of Work

Checkpoint the schema and reviews first. Extend the client and default terrain road classes. Wire a server-derived run extent to the Roads route and the existing control. Use established Roads field discovery. Amend the guide with actual control labels and a concrete field-edit example. Exercise the route and real artifact, capture the rendered control at desktop and phone widths, then have an independent usability reviewer inspect the images.

## Validation and acceptance

From the task worktree run wctl run-pytest against the changed topo, Roads and route paths, then tests --maxfail=1. Run wctl run-npm lint and test, rebuild controllers, and lint documentation. Save rendered evidence in artifacts. Reopen a downloaded GeoJSON, change model fields and verify upload readback and preservation of tags. Revert feature commits to roll back, with no data migration.

## Outcomes & Retrospective

Execution in progress.
