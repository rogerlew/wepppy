# Single User-Defined landuse and soils

The Config Builder checkbox **Enable single landuse and soils upload** enables
independent **Single User-Defined** choices in the Landuse and Soils controls.
It is a creation-time choice; existing projects keep their current behavior.

## Using uploaded inputs

Choose the upload mode in either control, select a file, and click Build.
Landuse accepts `.man` or `.MAN` management version 98.4; soils accepts `.sol` or
`.SOL` soil versions 2006, 2006.2, 7778, or 9002. Each source must contain exactly one OFE. The server
validates the actual contents, not just the extension. Files must be UTF-8 text,
at most 5 MiB. Windows line endings and a UTF-8 BOM are accepted. Management
2016.3 and later-format fields are not supported: the certified WEPP binary does
not consistently consume them.

Both 2006 versions require nine soil-header fields, including surface
conductivity (`avke`), and six values per layer. Version 9002 requires its
adjustment header and all seven appended hydraulic values per layer. Eight-field
2006.2 headers and incomplete 9002 records are rejected rather than repaired.
Version 9002 retains its supplied native conductivity-adjustment settings;
WEPPcloud adds no Disturbed parameterization. Uploaded hydraulic values are not
recomputed with Rosetta. Use ordinary quoted labels without embedded quotes or
backslash escapes; ambiguous native read-control syntax is rejected.

Each Build applies that source to all hillslopes and their OFEs. Multi-OFE projects
are supported up to 32 OFEs per hillslope. Landuse and soils remain independent:
one may use an uploaded source while the other uses an ordinary supported dataset.
Existing compatible cover, depth, conductivity, and saturation modifiers operate
on generated inputs. Explicit later hillslope edits retain their usual behavior;
building the upload mode again restores uniform assignments.

The accepted filename appears below the chooser and remains visible after reload.
A replacement is shown only after server acceptance. Rebuilding an accepted source
does not require selecting the file again. Rejected replacements preserve the
previous accepted source. If enqueueing fails after acceptance, reload to see the
accepted filename and retry Build. A failed job retains the source and normal job
error details. Read-only projects display the accepted filename without allowing
replacement.

## Project restrictions

Enabled projects use `wepp_260803`. They exclude Disturbed, SBS uploads, BAER,
Treatments, Omni scenarios/contrasts, PATH Cost-Effective, debris-flow models,
postfire debris flow, RUSLE, revegetation, and RRED. They also disable buffer OFE
geometry and management overrides, and the Disturbed-only Rosetta bulk-density
option. These restrictions apply even when both controls use ordinary modes.
Compatible independent features remain available. Changing a run mode or refreshing
configuration does not remove the creation-time restrictions.

## Operation and recovery

Accepted bytes live under `landuse/single-user-defined/` and
`soils/single-user-defined/` with SHA-256 filenames. The controller records the
original filename, digest, size, version, and relative source path. Normal
browse/download/archive operations include these files. Keep the module contents
and controller metadata together when copying or restoring a project.

Acceptance retains the current and immediately previous source generation.
Rebuild and mode changes preserve them. Missing or altered accepted sources cause
an explicit re-upload error. Do not repair the stored hash or silently substitute
a database input. Idle acceptance removes old unreferenced generations and a
bounded set of interrupted staging files; no background service is required.

Deploy the controller bundle, web/RQ code, and worker code together through the
existing deployment workflow. Restart long-lived workers when installing the new
enum values: an old worker cannot deserialize mode 5. Verify upload, actual RQ
completion, generated OFE counts, and native output using the deployed identities
and mounts before enabling the feature. Development acceptance uses a disposable
project and does not constitute production rollout approval.

## Developer contract

The authoritative behavior is [SUDI-01](../schemas/single-user-defined-inputs-contract.md).
Use the existing landuse/soil build endpoints and RQ jobs. Multipart admission is
bounded before generic form parsing; source publication is descriptor-relative,
uses immutable generation files and NoDb locking, and occurs under idle run
admission and module maintenance coordination. Active work returns 409; it is not
canceled to make room for an upload. Source metadata is additive and absent on
legacy projects; its `version` is the actual admitted soil version. Preparation
workers opt into `WeppSoilUtil(..., preserve_input_format=True)` for uploaded
soils, preserving native field layouts through saturation, conductivity and depth
modifiers. Ordinary catalog/Disturbed serialization retains its existing behavior.
Derived soil copies omit standalone source comments and blank lines to satisfy
native record ordering; immutable source bytes retain them. Modifier provenance
is written in the native-safe file header. Uploaded 9002 labels never suppress
explicit conductivity overrides. Deploy web and workers together when adding
formats; older workers cannot prepare these newly admitted sources.

Regression coverage includes parser limits, publication failures, source retention,
independent mode combinations, real generated files, native execution, Builder
refresh, UI transport after reload, escaped filename feedback, and exclusion guards.
