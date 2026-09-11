# Staley predictor artifact admission repair

Status: active. Repair the reported resource_limit failure on addicted-reservist.
Terrain construction succeeded; rainfall_io.load_predictors rejected the
74,129,489-byte generated slope TIFF against the rainfall 64 MiB cap.

Scope: use the operator-selected 96 MiB predictor raster cap for the three fixed predictor
TIFF artifacts, retain the 1 MiB summary/manifest cap and all rainfall/parquet
limits. Keep streaming hashes, nonsymlink ancestry and fixed allowlist checks.
No numerical policy, persisted schema or scientific parameter changes.

Plan: reviewed contract checkpoint, narrow implementation and boundary tests,
focused rainfall/results tests, actual project rerun through the UI, validation.
The last upload/status package is closed history and will not be edited.
