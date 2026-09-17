# Features Export Artifact Metadata

## Export summary

| Field | Value |
| --- | --- |
| Generated at (UTC) | 2026-09-17T03:01:23.962987+00:00 |
| Run ID | freshness |
| Config | test |
| Artifact ID | bb30e73373f7441897ad8307b096e36e |
| Format | geopackage |
| Artifact bundle | features_export.geopackage.zip |
| Cache hit | false |
| Source job ID | (none) |
| Units mode | si |
| Requested CRS | wgs |
| Resolved CRS | wgs |
| Resolved EPSG | (unspecified) |
| Packaged members | README.md, features_export.gpkg, manifest.json |

## Standards and interpretation notes

- This README follows the features export metadata baseline aligned to FGDC CSDGM essentials and ISO 19115-1 orientation.
- Machine-readable provenance is defined by `manifest.json`; this README is a deterministic derivative for human review.
- GeoPackage payload semantics follow OGC GeoPackage conventions and can be extended with `gpkg_metadata` tables.
- Resolved CRS mode is `wgs`.

## Resolved request profile

Normalized request payload:

```json
{
  "crs": "wgs",
  "format": "geopackage",
  "layers": [
    "test.attributes"
  ],
  "output_scopes": [
    "baseline"
  ],
  "swat_run_id": "none",
  "units": "si"
}
```

## Layer inventory

| Output layer | Source layer(s) | Scope / context | Rows | Features | Artifact member |
| --- | --- | --- | --- | --- | --- |
| freshness-sbs_map-subcatchments | test.attributes | baseline / base | 1 | 1 | features_export.gpkg |

## Column and unit summary

### freshness-sbs_map-subcatchments

- Source layer ids: `test.attributes`

| Column | Unit | Description |
| --- | --- | --- |
| topaz_id | non-unitized | Topaz ID. |
| wepp_id | non-unitized | WEPP ID. |
| id | non-unitized | ID. |
| value | non-unitized | Value. |


## Dependency lineage summary

| Field | Value |
| --- | --- |
| Dependency fingerprint | 188d1845aa7f2b6fd251c486d901959006c64d1f99d29a459d1c7d4c740ad255 |
| Catalog signature | 88b00e7ac05ca183b73dbedb180ce228ae0e04083e23f9643ba63be818cf5f68 |

### Role: geometry

| Dependency ID | Layer | Output layer | Relpath | Exists | Size | Hash |
| --- | --- | --- | --- | --- | --- | --- |
| geometry | test.attributes | shared__test.attributes | geometry.geojson | true | 181 | sha256:47ec91829467ec9886cda2cc433d7d473b65c1656f72a3a9224a7a22fd2c1d7c |

### Role: source

| Dependency ID | Layer | Output layer | Relpath | Exists | Size | Hash |
| --- | --- | --- | --- | --- | --- | --- |
| attrs | test.attributes | shared__test.attributes | attrs.parquet | true | 1726 | sha256:2188fb88d65dcbd6eb1f96c895d949421768a8d15b6468736ed3ae55ab8dfc4f |

## Warning summary

No warnings were reported for this artifact.

## Machine-readable contract pointer

`manifest.json` is the canonical machine-readable provenance and metadata contract for this artifact.
