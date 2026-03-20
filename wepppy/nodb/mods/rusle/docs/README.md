# RUSLE Reference Bundle

This directory is a local working cache of the primary open PDFs currently
used by the `Rusle` working specification in
[specification.md](../specification.md).

The immediate purpose is practical:

- keep the method references close to the module
- reduce future re-discovery work
- support manuscript drafting and methods review

This is not the source of truth for citations. The canonical citation list and
design rationale remain in [specification.md](../specification.md).

## Retrieved

- Retrieval date: `2026-03-20`
- Local PDF directory: [pdfs/](./pdfs/)

## Contents

| Local file | Reference | Source |
| --- | --- | --- |
| `pdfs/rusle2_science_doc.pdf` | USDA-ARS. *RUSLE2 Science Documentation*. | `https://www.ars.usda.gov/ARSUserFiles/60600505/rusle/rusle2_science_doc.pdf` |
| `pdfs/rusle2_handbook.pdf` | USDA-NRCS. *RUSLE2 Handbook*. | `https://www.nrcs.usda.gov/sites/default/files/2022-10/RUSLE2%20Handbook_0.pdf` |
| `pdfs/rusle2_user_reference_guide.pdf` | USDA-ARS. *RUSLE2 User Reference Guide*. | `https://www.ars.usda.gov/ARSUserFiles/60600505/RUSLE/RUSLE2_User_Ref_Guide.pdf` |
| `pdfs/national_agronomy_manual.pdf` | USDA-NRCS. *National Agronomy Manual*. | `https://www.nrcs.usda.gov/sites/default/files/2022-10/National-Agronomy-Manual.pdf` |
| `pdfs/wischmeier_smith_1978_ah537.pdf` | Wischmeier and Smith, 1978. *Predicting Rainfall Erosion Losses: A Guide to Conservation Planning*. | `https://www.ars.usda.gov/ARSUserFiles/60600505/RUSLE/AH_537%20Predicting%20Rainfall%20Soil%20Losses.pdf` |
| `pdfs/cligen_description.pdf` | USDA-ARS. *General Description of the CLIGEN Model and its History*. | `https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/cligen/cligendescription.pdf` |
| `pdfs/panda_2022_envsoft.pdf` | Panda et al., 2022. *Environmental Modeling & Software*, 155, 105413. | `https://www.srs.fs.usda.gov/pubs/ja/2022/ja_2022_amatya_005.pdf` |
| `pdfs/mukherjee_2025_envsoft.pdf` | Mukherjee et al., 2025. *Environmental Modeling & Software*, 183, 106243. | `https://www.srs.fs.usda.gov/pubs/ja/2025/ja_2025_devendra_001.pdf` |
| `pdfs/shojaeezadeh_2024_preprint.pdf` | Shojaeezadeh et al., 2024 preprint for *Catena* 242, 108074. | `https://opus.lib.uts.edu.au/bitstream/10453/167179/2/2207.06579v1.pdf` |
| `pdfs/benavidez_2018_hess_rusle_review.pdf` | Benavidez et al., 2018. *Hydrology and Earth System Sciences*, 22, 6059-6086. | `https://hess.copernicus.org/articles/22/6059/2018/hess-22-6059-2018.pdf` |
| `pdfs/panagos_2015_geosciences_ls_factor.pdf` | Panagos et al., 2015. *Geosciences*, 5(2), 117-126. | `https://pdfs.semanticscholar.org/634d/c2d4b3982eddd93e66ef5db748ba264907ea.pdf` |
| `pdfs/rossiter_2022_soil_dsm_geography.pdf` | Rossiter et al., 2022. *SOIL*, 8, 559-586. | `https://soil.copernicus.org/articles/8/559/2022/soil-8-559-2022.pdf` |
| `pdfs/sda_table_column_descriptions.pdf` | USDA-NRCS. *Soil Data Access Related Tables: Table Column Descriptions*. | `https://sdmdataaccess.nrcs.usda.gov/documents/TableColumnDescriptionsReport.pdf` |
| `pdfs/nlcd_classes.pdf` | MRLC. *National Land Cover Database Class Legend and Description*. | `https://www.mrlc.gov/sites/default/files/NLCDclasses.pdf` |

## Notes

- `Panagos et al. (2015)` was mirrored from an alternate open PDF host because
  the publisher PDF endpoint returned `403` to scripted retrieval on
  `2026-03-20`.
- Some references used by the specification are HTML pages or non-open
  publisher landing pages and are therefore not mirrored here. Examples
  include `SWAT+` theoretical docs, `GRASS` and `SAGA` manuals, `gSSURGO` and
  `gNATSGO` product pages, and the EPA wetlands guidance page.
- If this bundle is refreshed later, keep filenames stable where possible so
  manuscript notes and local references do not drift.
