---
marp: true
theme: gaia
paginate: true
size: 16:9
---

# Introduction to WEPPcloud

Physics-based watershed modeling in a browser

University of Idaho + USDA Forest Service collaboration

---

# WEPPcloud turns watershed setup into a repeatable workflow

- Free, web-based platform for runoff and erosion modeling
- Converts map selection into ready-to-run watershed inputs
- Uses the WEPP modeling stack with integrated geospatial and climate data
- Built for scenario comparison (baseline vs treatment / disturbance)

---

# WEPPcloud is developed by research and operations partners

- Primary development: University of Idaho + USDA Forest Service RMRS
- Additional contributions: USDA ARS, Swansea University, Michigan Tech
- Publicly funded research infrastructure (no subscription tier)

---

# WEPPcloud supports applied decisions across multiple domains

- Pre-fire planning and treatment comparison
- Post-fire response (BAER-aligned workflows)
- Utility and municipal watershed management
- Academic watershed and erosion research
- Agriculture and disturbed-land analysis

---

# Core modeling capabilities in WEPPcloud

- **WEPP:** hillslope + watershed hydrology and erosion
- **WATAR / Ash Transport:** post-fire ash and contaminant transport
- **Debris Flow mod:** post-fire debris-flow probability and volume screening
- **WEPP/SWAT+:** coupled workflow support for SWAT+ runs
- **Gridded RUSLE mod:** raster-based erosion-potential factors and outputs

---

# Typical project lifecycle

- Delineate channels, outlet, and subcatchments
- Build landuse, soils, and climate
- Run WEPP and review mapped outputs
- Fork scenarios to compare management alternatives
- Export GIS/tabular products for downstream analysis

---

# FAQ: watershed size guidance is practical, not just computational

- Recommended upper bound: ~2,500 hillslopes
- Legacy rule of thumb: about 50 square miles or less per run
- Runtime is often the limiting factor on large projects
- Larger delineations are possible, but interpretation risk increases

---

# FAQ: important limitations to communicate clearly

- Reservoir routing/settling impacts are not modeled in the main watershed workflow
- Carbon and nitrogen cycling are not simulated in the watershed interface
- Direct landslide simulation is not included
- Debris-flow hazard is available through a dedicated post-fire module

---

# Use WEPPcloud when you need defensible scenario comparisons

- Strong fit: relative change across treatments/scenarios
- Strong fit: watershed-scale planning support
- Caution: decisions requiring reservoir dynamics, C/N cycling, or landslide mechanics

---

# Thank you

Questions?

Contact: WEPPcloud team (University of Idaho / USDA Forest Service RMRS)
