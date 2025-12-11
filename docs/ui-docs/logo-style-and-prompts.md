# Logo Style Guide and AI Generation Prompts
> WEPPcloud Unified Logo System

## Overview

This document defines a cohesive visual identity for WEPPcloud's logo ecosystem, covering:
- **Interface logos**: Visual representations of each WEPPcloud modeling interface
- **Affiliate/partner logos**: Third-party organization logos (use originals, not regenerated)
- **Sponsor logos**: Funding agency logos (use originals, not regenerated)

### Current State Assessment

The existing logo collection suffers from:
1. **Inconsistent dimensions**: Ranging from 63×68px to 3840×2160px
2. **Mixed formats**: PNG, SVG, JPG, GIF, WebP without clear rationale
3. **Varied visual styles**: Some photographic, some illustrated, some abstract
4. **Inconsistent color palettes**: No unified theme across interface icons
5. **Resolution mismatches**: Some logos pixelated, others unnecessarily large

---

## Unified Logo Design System

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Cohesion** | All interface logos share a recognizable visual language |
| **Scalability** | Vector-first (SVG) with PNG exports for compatibility |
| **Accessibility** | Sufficient contrast, clear shapes at small sizes |
| **Dark-mode ready** | Works on both light and dark backgrounds |
| **Environmental** | Conveys water, earth, erosion, fire, or landscape themes |

### Color Palette

**Primary Colors** (from WEPPcloud brand):
- **Ocean Blue**: `#0369a1` (sky-700) — water, hydrology
- **Earth Brown**: `#78350f` (amber-900) — soil, erosion
- **Forest Green**: `#166534` (green-800) — vegetation, land cover
- **Flame Orange**: `#c2410c` (orange-700) — fire, burn severity
- **Slate Gray**: `#334155` (slate-700) — neutral, technical

**Accent Colors**:
- **Ash Gray**: `#6b7280` (gray-500) — WATAR, ash transport
- **Rangeland Tan**: `#d97706` (amber-600) — RHEM, rangelands
- **Ice Blue**: `#0ea5e9` (sky-500) — climate, precipitation

### Standard Dimensions

| Use Case | Dimensions | Format |
|----------|------------|--------|
| Interface card | 400×400px | SVG + PNG |
| Navigation icon | 32×32px | SVG |
| Favicon | 16×16, 32×32, 180×180px | PNG + ICO |
| Social/OG image | 1200×630px | PNG |

### Visual Style

**Style**: Flat/semi-flat illustration with subtle gradients
**Stroke**: Consistent 2-4px stroke weight at 400px size
**Corners**: Rounded corners (8-16px radius) for a modern feel
**Shadows**: Minimal, soft drop shadows only for depth (optional)
**Iconography**: Abstract landscape silhouettes, topographic lines, water flow patterns

---

## Logo Categories

### Category 1: Interface Logos

These logos appear on the `/interfaces/` page and represent each WEPPcloud modeling interface.

### Category 2: Affiliate Logos (Do Not Regenerate)

Third-party logos from universities and agencies. **Use official logos from each organization.** Apply consistent sizing and optional grayscale filtering for uniformity.

| Organization | Current File | Notes |
|--------------|--------------|-------|
| University of Idaho | `University_of_Idaho_logo.svg` | SVG ✓ Good |
| Swansea University | `Swansea_University_logo.png` | PNG, consider SVG source |
| USDA Forest Service | `Logo_of_the_United_States_Forest_Service.svg` | SVG ✓ Good |
| UI RCDS | `RCDS_Logo-horizontal.svg` | SVG ✓ Good |
| Rangeland Analysis Platform | `rapIconSmall.png` | PNG 384×384, decent |
| Michigan Tech | `michigan-tech-logo-full-yellow.svg` | SVG ✓ Good |
| Washington State University | `Washington-State-University-Logo.png` | PNG 3840×2160, oversized |

### Category 3: Sponsor Logos (Do Not Regenerate)

Funding agency logos. **Use official logos from each agency.** Standardize sizing.

| Organization | Current File | Notes |
|--------------|--------------|-------|
| NSF Idaho EPSCoR | `Idaho_epscor_logo_no_white_background.png` | PNG 406×174 |
| USDA NIFA | `USDA_logo.png` | PNG 320×219 |
| UKRI NERC | `ukri-nerc-logo-600x160.png` | PNG 600×160 |
| NASA WWAO | `nasa_logo.svg` | SVG ✓ Good |

---

## Interface Logo Prompts

The following prompts are designed for AI image generation tools (DALL-E, Midjourney, Stable Diffusion). Each prompt follows a consistent structure for unified results.

### Base Prompt Template

```
A minimalist flat illustration logo for [INTERFACE NAME], featuring [KEY VISUAL ELEMENTS]. 
Style: modern flat design with subtle gradients, clean geometric shapes, [COLOR PALETTE].
The composition shows [SCENE DESCRIPTION].
Background: [BACKGROUND COLOR OR TRANSPARENT].
No text, no labels, professional icon style, suitable for web UI at 400x400 pixels.
```

---

### Prompt 1: WEPPcloud-(Un)Disturbed

**Current file**: `interfaces/disturbed.png` (200×200px)
**Purpose**: Primary US interface for pre/post-fire erosion modeling with WATAR

```
A minimalist flat illustration logo for watershed erosion modeling.
Style: modern flat design with subtle gradients, clean geometric shapes.
Color palette: earth brown (#78350f) and flame orange (#c2410c) with slate gray (#334155) accents.
The composition shows a stylized hillslope cross-section with visible soil layers, 
subtle erosion channels flowing downward, and a hint of fire/burn gradient at the top transitioning 
to healthy vegetation at the bottom. Topographic contour lines in the background suggest terrain.
Include abstract rain droplets and small sediment particles.
Background: transparent or soft slate (#1e293b).
No text, no labels, professional icon style, suitable for web UI at 400x400 pixels.
```

**Keywords**: hillslope, soil layers, erosion channels, fire gradient, vegetation, topographic

---

### Prompt 2: WEPPcloud-Revegetation

**Current file**: `interfaces/revegetation.webp` (1024×1024px)
**Purpose**: Post-fire recovery modeling with RAP vegetation data

```
A minimalist flat illustration logo for post-fire vegetation recovery modeling.
Style: modern flat design with subtle gradients, clean geometric shapes.
Color palette: forest green (#166534) transitioning from burned orange (#c2410c) 
with fresh growth lime (#84cc16) accents.
The composition shows a landscape timeline from left to right: charred/burned hillside 
on the left transitioning to recovering shrubs in the middle to healthy green forest on the right.
Small plant sprouts emerge from the soil. Subtle timeline arrow or growth curve motif.
Abstract rain cloud providing moisture for recovery.
Background: transparent or soft slate (#1e293b).
No text, no labels, professional icon style, suitable for web UI at 400x400 pixels.
```

**Keywords**: recovery, timeline, burned to green, sprouts, growth, moisture

---

### Prompt 3: WEPPcloud-EU (Europe)

**Current file**: `interfaces/europe.png` (512×512px)
**Purpose**: European interface using ESDAC data

```
A minimalist flat illustration logo for European watershed erosion modeling.
Style: modern flat design with subtle gradients, clean geometric shapes.
Color palette: ocean blue (#0369a1) and forest green (#166534) with gold (#fbbf24) accents.
The composition shows a stylized European landscape with rolling Mediterranean hills,
subtle outline of Europe as a landmass silhouette. Topographic contour lines and 
water flow channels. Small EU stars motif subtly integrated.
Olive trees or vineyards on terraced slopes. Erosion runoff into a river or coast.
Background: transparent or soft slate (#1e293b).
No text, no labels, professional icon style, suitable for web UI at 400x400 pixels.
```

**Keywords**: Europe, Mediterranean, terraces, olive trees, EU stars, coastal

---

### Prompt 4: WEPPcloud-AU (Australia)

**Current file**: `interfaces/australia200.png` (200×200px)
**Purpose**: Australian interface using ASRIS data

```
A minimalist flat illustration logo for Australian watershed erosion modeling.
Style: modern flat design with subtle gradients, clean geometric shapes.
Color palette: burnt orange (#ea580c) and outback red (#b91c1c) with eucalyptus green (#22c55e) accents.
The composition shows an Australian outback landscape with distinctive red earth and ochre tones.
Rolling arid hills with sparse eucalyptus trees (gum trees) and iconic boab or ghost gum silhouettes.
Dry creek bed with seasonal water flow patterns indicated by dashed lines.
Erosion gullies cutting through red soil. Small kangaroo silhouette as subtle accent in the distance.
Background: transparent or soft slate (#1e293b).
No text, no labels, no country outline, no map shape, professional icon style, suitable for web UI at 400x400 pixels.
```

**Keywords**: Australia, outback, red earth, eucalyptus, gum trees, arid, erosion gullies, kangaroo

---

### Prompt 5: WEPPcloud-RHEM (Rangeland)

**Current file**: `interfaces/rhem.png` (150×44px) — undersized text logo
**Purpose**: Rangeland Hydrology and Erosion Model

```
A minimalist flat illustration logo for rangeland erosion modeling.
Style: modern flat design with subtle gradients, clean geometric shapes.
Color palette: rangeland tan (#d97706) and sage green (#84cc16) with earth brown (#78350f) accents.
The composition shows a semi-arid rangeland landscape with sparse shrubs and bunchgrasses.
Rolling hills with visible erosion rills between vegetation patches.
Cattle grazing silhouettes in the background (small, subtle).
Rain event with water infiltrating and running off exposed soil.
Background: transparent or soft slate (#1e293b).
No text, no labels, professional icon style, suitable for web UI at 400x400 pixels.
```

**Keywords**: rangeland, shrubs, bunchgrass, grazing, semi-arid, infiltration

---

### Prompt 6: Lake Tahoe Site-Specific

**Current file**: `interfaces/lt.jpg` (150×150px)
**Purpose**: Lake Tahoe region-specific modeling

```
A minimalist flat illustration logo for Lake Tahoe watershed modeling.
Style: modern flat design with subtle gradients, clean geometric shapes.
Color palette: deep blue (#0369a1) and alpine green (#166534) with snow white (#f8fafc) accents.
The composition shows Lake Tahoe as a distinct blue oval surrounded by forested mountains.
Snow-capped Sierra peaks in the background. Pine tree silhouettes along the shoreline.
Phosphorus/nutrient flow indicated by subtle particles moving toward the lake.
Clear mountain stream feeding into the lake.
Background: transparent or soft slate (#1e293b).
No text, no labels, professional icon style, suitable for web UI at 400x400 pixels.
```

**Keywords**: Lake Tahoe, alpine, Sierra, pine forest, mountain lake, phosphorus

---

### Prompt 7: Hazard SEES / FireEarth

**Current file**: `interfaces/widlfire_credit_NOAA_DanBorsum.jpg` (200×200px)
**Purpose**: Municipal watershed wildfire hazard modeling

```
A minimalist flat illustration logo for wildfire watershed hazard modeling.
Style: modern flat design with subtle gradients, clean geometric shapes.
Color palette: flame orange (#c2410c) and smoke gray (#6b7280) with water blue (#0ea5e9) accents.
The composition shows a dramatic mountain watershed with active wildfire on ridges.
Smoke plumes rising and drifting. Below, a reservoir or municipal water intake.
Ash and sediment flowing into water supply. Warning/hazard motif subtly integrated.
Urban silhouette in the distance representing the city water supply at risk.
Background: transparent or soft slate (#1e293b).
No text, no labels, professional icon style, suitable for web UI at 400x400 pixels.
```

**Keywords**: wildfire, municipal watershed, reservoir, smoke, ash transport, urban

---

### Prompt 8: Legacy WEPPcloud (Baseline)

**Current file**: `interfaces/0.jpg` (200×200px)
**Purpose**: Original WEPP interface (deprecated but still available)

```
A minimalist flat illustration logo for watershed erosion prediction.
Style: modern flat design with subtle gradients, clean geometric shapes.
Color palette: slate gray (#334155) and muted blue (#64748b) with earth brown (#78350f) accents.
The composition shows a dramatic bird's-eye view of a watershed carved into mountain terrain.
Bold dendritic stream network branching like tree roots or veins across the landscape.
Layered hillslope ridges with visible erosion scarring. Sediment plumes at channel confluences.
Rain clouds gathering at the headwaters with stylized precipitation falling.
A sense of timeless, foundational hydrology—the original watershed science aesthetic.
Background: transparent or soft slate (#1e293b).
No text, no labels, professional icon style, suitable for web UI at 400x400 pixels.
```

**Keywords**: watershed, dendritic, stream network, hillslopes, mountain terrain, sediment plumes, classic hydrology

---

### Prompt 9: Agricultural Fields

**Current file**: None (new interface)
**Purpose**: Agricultural field-scale erosion modeling

```
A minimalist flat illustration logo for agricultural field erosion modeling.
Style: modern flat design with subtle gradients, clean geometric shapes.
Color palette: golden wheat (#eab308) and rich soil brown (#78350f) with crop green (#22c55e) accents.
The composition shows a stylized agricultural landscape with geometric crop field patterns.
Parallel furrows or contour strips visible from above. Tractor tire tracks or tillage lines.
Visible soil erosion between crop rows with sediment transport indicated.
Cover crop or stubble texture on some fields. Subtle rain event with runoff flowing downslope.
Farm equipment silhouette (small tractor or combine) as tiny accent.
Background: transparent or soft slate (#1e293b).
No text, no labels, professional icon style, suitable for web UI at 400x400 pixels.
```

**Keywords**: agriculture, crop fields, furrows, tillage, contour farming, sediment, tractor

---

### Prompt 10: WEPPcloud-PEP / BAER

**Current file**: `interfaces/baer.jpg` (530×530px)
**Purpose**: Post-fire erosion prediction (legacy BAER support)

```
A minimalist flat illustration logo for post-fire erosion emergency assessment.
Style: modern flat design with subtle gradients, clean geometric shapes.
Color palette: fire red (#dc2626), char black (#18181b), and warning yellow (#facc15) with recovery green (#22c55e) accents.
The composition shows a burned hillslope with visible burn severity zones.
Four distinct severity bands (unburned → low → moderate → high).
Erosion channels forming in the burned areas. First responder/emergency feel.
Small shovel or assessment tool icon integrated subtly.
Background: transparent or soft slate (#1e293b).
No text, no labels, professional icon style, suitable for web UI at 400x400 pixels.
```

**Keywords**: BAER, burn severity, emergency, four zones, erosion channels, assessment

---

## Implementation Guide

### File Naming Convention

```
interfaces/
├── disturbed.svg         # Primary SVG
├── disturbed.png         # 400x400 PNG export
├── disturbed-32.png      # 32x32 navigation icon
├── revegetation.svg
├── revegetation.png
├── europe.svg
├── europe.png
├── australia.svg
├── australia.png
├── rhem.svg
├── rhem.png
├── lake-tahoe.svg
├── lake-tahoe.png
├── fireearth.svg
├── fireearth.png
├── legacy-weppcloud.svg
├── legacy-weppcloud.png
├── baer-pep.svg
└── baer-pep.png
```

### Generation Workflow

1. **Generate candidates**: Use prompts above with DALL-E 3, Midjourney v6, or Stable Diffusion XL
2. **Select best result**: Choose image that best matches design principles
3. **Vectorize**: Use Vectorizer.ai or Adobe Illustrator Image Trace to convert to SVG
4. **Clean up**: Remove artifacts, standardize colors to palette, ensure 400×400 artboard
5. **Export**: Save SVG and export PNG at 400×400, 32×32, and 16×16
6. **Validate**: Test on light/dark backgrounds, verify accessibility contrast

### CSS Integration

```css
/* Interface logo card styling */
.wc-feature__media img {
  width: 200px;
  height: 200px;
  object-fit: contain;
  border-radius: 8px;
  background: var(--surface-secondary);
}

/* Dark mode grayscale filter for affiliates (landing page) */
.affiliate-logo {
  filter: grayscale(1) invert(1) opacity(0.6) contrast(1.25);
}
```

---

## Affiliate Logo Standardization

While affiliate logos should not be AI-regenerated (use official sources), they should be standardized:

### Recommended Actions

| Logo | Action Required |
|------|-----------------|
| `Washington-State-University-Logo.png` | Resize from 3840×2160 to max 600px width |
| `usfslogo.png` | Low res (63×68), replace with `Logo_of_the_United_States_Forest_Service.svg` |
| `Swansea_University_logo.png` | Request SVG from university or keep PNG |
| `rapIconSmall.png` | Acceptable, consider SVG if available |

### Standardized Sizing

All affiliate logos should be processed to:
- **Max height**: 80px (for inline display)
- **Max width**: 200px
- **Format**: SVG preferred, PNG acceptable
- **Background**: Transparent

---

## Quality Checklist

Before deploying new logos:

- [ ] SVG and PNG versions exist
- [ ] Colors match defined palette (±5% variance acceptable)
- [ ] Visible at 32×32px (nav icon size)
- [ ] Works on both `#0f172a` (dark) and `#f8fafc` (light) backgrounds
- [ ] No text embedded in the image
- [ ] File size < 100KB for PNG, < 20KB for SVG
- [ ] Consistent visual style with other interface logos
- [ ] Accessible contrast ratio (4.5:1 minimum for key elements)

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-11 | GitHub Copilot | Initial document creation |

---

## See Also

- [UI Style Guide](ui-style-guide.md) — Overall WEPPcloud design system
- [Theme System](theme-system.md) — VS Code theme integration
- [Landing Spec](../../weppcloud-ui-lab/landing.spec.md) — Landing page design specification
