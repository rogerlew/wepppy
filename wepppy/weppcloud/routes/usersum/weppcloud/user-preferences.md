# User Preferences

> Set the units you see and the WBT boundary behavior for work you submit.

## Open the page

Sign in, open **Profile**, and select **User Preferences**. Preferences apply
to you across projects you are authorized to use. They do not rewrite a
project's saved settings.

## Default units

- **Auto — use project configuration** keeps the unit choice supplied by the
  project.
- **SI — metric defaults** displays metric defaults.
- **English — US customary defaults** displays US customary defaults.

SI and English affect your view of existing, shared, forked, and new projects.
They do not change the project's saved Unitizer selections. Another user may
view the same project in different units. Choose Auto to see the project's
saved unit choices.

## WBT watershed boundary behavior

WBT can identify a delineated watershed whose hillslopes touch the edge of the
DEM. That may mean the actual watershed continues outside the selected map
extent.

- **Auto — use project configuration** uses the project's behavior.
- **Warn and continue** keeps the delineation and shows the affected edge
  hillslope identifiers.
- **Stop with an error** removes the clipped subcatchment raster and stops
  watershed abstraction.

If delineation stops, select an outlet farther from the DEM boundary or enlarge
the project extent, then build channels and delineate again.

Warn/Stop is resolved when you submit delineation. It follows the initiating
user, not the project owner, and does not become another user's preference.

## Save and verify

Select both defaults and choose **Save preferences**. A confirmation appears
after the page reloads. Your next authorized project view and next WBT
delineation submission use the saved choices. Work already queued keeps the
snapshot it received when submitted.

See [Channel Delineation](controls/channel-delineation.md) for extent,
conditioning, and boundary troubleshooting.
