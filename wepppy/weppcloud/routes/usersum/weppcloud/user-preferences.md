# User Preferences

> Set account defaults for units and WBT watershed boundary handling.

## Open the page

Sign in, open **Profile**, and select **User Preferences**. Preferences apply
only when you create a new project. Existing projects, shared projects, and
forked projects keep their saved settings.

## Default units

- **Auto — use project configuration** keeps the unit choice supplied by the
  selected project configuration.
- **SI — metric defaults** starts new projects with metric defaults.
- **English — US customary defaults** starts new projects with US customary
  defaults.

An explicit unit choice on a project-creation form takes precedence over this
account default.

## WBT watershed boundary behavior

WBT can identify a delineated watershed whose hillslopes touch the edge of the
DEM. That may mean the actual watershed continues outside the selected map
extent.

- **Auto — use project configuration** uses the behavior selected by the
  project configuration.
- **Warn and continue** keeps the delineation and shows the affected edge
  hillslope identifiers.
- **Stop with an error** removes the clipped subcatchment raster and stops
  watershed abstraction.

If delineation stops, select an outlet farther from the DEM boundary or enlarge
the project extent, then build channels and delineate again.

## Save and verify

Select both defaults and choose **Save preferences**. A confirmation appears
after the page reloads. The defaults are copied into each new project, so later
preference changes do not alter runs that already exist.

See [Channel Delineation](controls/channel-delineation.md) for extent,
conditioning, and boundary troubleshooting.
