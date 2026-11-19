# Original-project disposable replay

Status: complete local workflow and artifact readback; original unchanged.

Source: read-only copy from wepp1's
`/geodata/wc1/runs/qu/quasi-religious-allotment`.
Disposable run: `/wc1/runs/so/soil-capacity23-quasi-20261118`.
Final executable selection: matched `wepp_261118` pair (see release identity).

The original had no climate or station selected. The operator explicitly
approved nearest CLIGEN station for disposable validation: canonical lookup
selected ALCALDE NM (`nm290245`, approximately 32.39 km). Generated 100 years
contain 36,524 days. These are execution-validation results, not an approved
scientific result for the original project.

## Observed artifacts

- Actual soil-build RQ job `285392cf-ad02-4c00-aecb-821bd335d661` passed.
  It wrote 196 raw soils; eight have eleven horizons after the 200 mm split.
- Preparation produced 355 hillslope soils and a 144-OFE channel soil.
  Selected hillslope soils in this particular project each have at most ten
  horizons. Separate real Puaulu tests exercise 21 through prepared/MOFE/native
  paths; this replay alone does not prove that dimension.
- All 355 native hillslope simulations and the watershed completed 100 years.
  Native watershed elapsed time was 817.03 seconds.
- All six canonical RQ post-processing stages passed: hillslope interchange,
  total water/sediment, hillslope water balance, watershed interchange,
  GeoPackage export and loss grid.
- Actual hill/channel/outlet report consumers loaded 355/144 rows and finite
  outlet values. Controller `has_run` is true.
- Streaming readback verified all 5,259,456 channel daily records are finite
  and every channel calendar matches the generated climate, without missing
  or duplicate days. All 356 prepared soil files pass the capacity parser.

Full receipts, input SHA-256 manifest and output readback are retained in
`/workdir/soil-input-capacity-23-evidence/replay-output-readback.json`.
Raw channel/loss outputs are retained by hardlink under the disposable run's
`.capacity-evidence/raw/` before canonical interchange cleanup. Normal reports,
exports and prepared inputs remain in the canonical run directories.

## Runtime and limitations

App code ran as UID 1002, GID 130, supplementary group 130, umask 002 in a
one-shot development rq-worker with the task checkout and a read-only executable
view. Host development secret files were copied privately inside the disposable
container before dropping identity; no secrets are retained in evidence.
Only this clone's coordination lock files were provisioned for the worker.
No global directory permission change or original-project mutation was made.

Copied NoDb identities were rebased with canonical fork helpers and the copied
query catalog incarnation invalidated. SDA was unavailable, so SQLite backup of
the copied source cache supplied the clone's existing cache interface. Records
were not invented. The worker image/configuration are development equivalents;
this is not a claim of production deployment parity.

The initial manual replay omitted hillslope interchange before watershed
post-processing, which failed explicitly on missing `H.pass.parquet` after the
native model succeeded. The canonical six RQ post-jobs were then executed in
order against the completed outputs. No native model rerun or fabricated PASS
file was needed. Logs retain the failure and successful continuation.
