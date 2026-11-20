# Forest development deployment and incident replay

## Deployment

On 2026-11-20 UTC, the installed `wctl` dev preset built and brought up the
full selected forest stack from candidate
`af514e39c29c9bb4b7f26ab9ca84bc9b21826d40`. The RQ, worker and web runtime
used image
`sha256:808d66b77538183a1eeddd6f58baa7e6db32cfee845d7ddf2c91d20158838ad2`.
The default, batch and fork queues were idle before the worker cutover.
The effective configuration selected 28 services. Frontend compilation
passed, both build-only containers exited successfully and the running
services passed web and RQ HTTP checks. Compose's initial health wait
returned when a build-only container exited. A normal full Compose up
completed and runtime checks verified the result.

Forest metquery mounted the regenerated E-OBS v19.0e tree read-only with
96 WGS84 GeoTIFFs and eight relocatable VRTs. Independent January and August
readback compared all fields at four locations with masked NetCDF controls.
The candidate worker retrieved a 12-month response using forest metquery.
The native jobs used `wepp_31131a7`. Production projects and data remained
untouched.

## Original workflow replay

[ontological-swing on forest](https://forest.tail305ec9.ts.net/weppcloud/runs/ontological-swing/eu-disturbed/)
used the archived `MDT5m.tif` (SHA-256
`f4ed3d5e181e5e3ae89fe766bd6caf1014947b99dc92a1221b7b9444b1cbc3fd`),
outlet, extent mode 3, TOPAZ `ifolp`, MCL 100, CSA 5, and the archived
flowpath and channel-width options. All 58 hillslope IDs, areas and lengths
matched. The 23 channel IDs matched, with maximum area and length differences
of 7.64962477 in the stored area field and 22.3606798 m. CORINE switched 2018 → 2012 → 2018. Both
gridded ESDAC builds produced 58 soils, with 37 defaults and 21 source
profiles. The browser showed the count, Soil Quality Details and the Advanced
options location. The primary replay then applied the original Forest loam
database override.

| Operation | Result | RQ job |
| --- | --- | --- |
| First individual event WEPP after two `FLOOD4.cli` uploads | Advisory shown and watershed output completed | `a43256c6-5268-49ea-8f66-892674b781f1` |
| Three E-OBS builds | All finished | `f047baac-7243-4166-a662-861dfbf3873f`, `4d888ed5-bb37-4144-b1f2-a439ad80263b`, `414d21d8-0fd6-471c-9018-066f19cd3125` |
| Individual event WEPP after third `FLOOD4.cli` upload | Completed again | `1307390c-c1a5-4856-adaa-3abdd8ad7319` |
| Original `ESFANGAR.cli` upload | Browser reload showed the file and cleared the event advisory | `b9ce774c-edfd-4e4a-b4f5-8c0f5a35bc3e` |
| Final continuous WEPP and reports | Completed | `fcefd2b9-142d-4234-91e5-9ac0da3ac33a` |

The first event readback found exact original climate bytes in the prepared
hillslope deck, 58 hillslope pass/event outputs, a 27,827-byte native watershed
loss file and a 696-byte event output. The final replay consolidated one
duplicate continuous submission from the original history.

[declassified-ruse on forest](https://forest.tail305ec9.ts.net/weppcloud/runs/declassified-ruse/eu-disturbed/)
forked the primary replay after gridded soils and before the override. Station
`SPE00119882` generated 30 years (job
`3d4f3dd0-5231-4be5-be83-cbf4e246981c`). Actual WEPP job
`bf207ab9-a980-4f5e-a4b4-c66c4d84162d` prepared and ran that climate and
the gridded soils.

| Direct artifact readback | Continuous upload | Gridded soils and E-OBS |
| --- | --- | --- |
| Climate SHA-256 in each of 59 prepared decks | `1b6329e1509b6f6527e4ce00016c4d48492c7373ff5a542fd3e0f6ca455732b2` | `69de607b1bd4056f4f80d9a79aad92e8394a8dcf05fb87fec96245df56b8f339` |
| Valid daily climate rows | 10,957 | 10,957 |
| Parsed format-7778 prepared soil decks | 59 | 59 |
| Native hillslope pass outputs | 58 | 58 |
| Native watershed loss bytes | 623,882 | 606,047 |
| Rows in each watershed EBE and totalwatsed Parquet | 10,957 | 10,957 |
| Hillslope pass Parquet rows | 635,506 | 635,506 |

## Land-use and climate status controls

[cleft-jump on forest](https://forest.tail305ec9.ts.net/weppcloud/runs/cleft-jump/eu-disturbed/)
used the retained CORINE raster as a substitute for the missing original
`LandCover25m.tif`. The incompatible ESDAC upload selection still reached
and failed in the worker (`c6737c76-0bbc-4f96-921d-bacedbe08a1b`), with the
fresh project's normal Landuse controls available after reload. Switching
to gridded CORINE 2018 (`17f49743-64bc-4f2c-8bcc-74f58d127c82`) produced a
58-row Parquet. All 16 class-25 rows resolved to Mixed forest with
`UnDisturbed/Old_Forest.man` and Disturbed class `forest`. A separate
private serialized legacy control generated Parquet through the migration.
Early incompatible-upload feedback and exact original raster fidelity remain
open.

The browser initially showed failed E-OBS job
`6de447d5-9bac-400a-9014-4bcdca1ec2fc` from a controlled missing station.
The first replacement upload encountered a transient NoDb lock. A normal
retry succeeded (`3eae0478-0c84-4cf1-b1da-5e21a92e14ae)). The reloaded
browser showed `ESFANGAR.cli` and the latest successful operation, with
the old failure details absent. A failed generated rebuild after an earlier
accepted climate is a separate publication and readiness case.

Restricted evidence is retained on forest under
`/var/tmp/wepppy-eu-run-recovery-baseline`, including Compose receipts,
replay progress, `forest-completed-native-readback.json`,
`gridded-soil-warning.png`, `partial-landuse-no-migration.png` and
`controlled-climate-reload-file-page.png`. The broad pytest run stopped
at a culvert lock error also reproduced on the unchanged base, after
369 passed and 28 skipped.

Independent read-only review verified the two continuous runs, the archived
event inputs and native outputs, the CORINE recovery artifact and the
failed-build-to-upload browser transition. The transient NoDb lock remains
a separate reliability finding.

## Updated uploaded land-use replay

Forest next loaded `80e2a01cf` in the Web, RQ and worker services.
A signed-in browser on `cleft-jump` tested the retained CORINE source
through Upload landcover map. Class 999 returned actionable HTTP 400
before queue admission, while the applied report stayed in the page.
The matching CORINE upload finished as RQ job
`83c971a2-4115-4904-ace2-c823bcdb5292`. Readback verified the exact
submitted raw raster, the aligned TIFF digest from the job's receipt and
only the compact receipt remaining in its staging directory. The
current upload produced 58 land-use Parquet rows, including 16 Mixed
forest assignments for class 25. The browser reported the result. Direct
artifact and screenshot evidence are in
`forest-landuse-staged-native-readback.json` and
`landuse-staged-mixed-forest.png` in the restricted directory.

The related private response and worker controls proved stale receipt
rejection, exact same-ID retry, cleanup, managed projection containment
and a fresh batch leaf with its own alignment. Focused land-use tests
passed 95 cases. Frontend tests passed 127 suites and 1,109 tests,
plus nine Node tests. The broad test run passed 839 and skipped 32
before stopping at a browse download diagnostics assertion.

Forest RQ workers then loaded `def92f11e` for the CLIGEN worker-directory
fix. The next native Es Fangar build and its browser report finished
with station `SPE00119882` and without the event advisory
(`ccfda21a-7c03-45ba-9eee-1c6b5b5202a6`). WEPP job
`84f4863f-1dd6-48b1-9b07-2ba89be55324` and all 17 children finished.
The second native readback again found 10,957 daily rows, 59 matching
climate decks, 59 parsed soils, and 635,506 hillslope pass records.
See the
[failed generated replacement control](20261120_eobs_publication_checkpoint.md#retained-failure-controls)
for the observed behavior after a failed rebuild and the operator’s scope clarification.

The final frontend bundle showed the batch settings acknowledgement as
status and ignored a late stale rejection in the controller tests. Forest
served the rebuilt bundle with the same SHA-256 as the candidate. A second
signed-in invalid/valid upload control finished with RQ job
`debe1082-2e36-4a09-b97a-92f5e02beac7` and the same 58-row Parquet,
including 16 Mixed forest assignments.
