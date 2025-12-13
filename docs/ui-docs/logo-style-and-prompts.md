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

**Files**: `interfaces/disturbed.svg`, `interfaces/disturbed.png` (400×400px) ✓ Generated
**Purpose**: Primary US interface for pre/post-fire erosion modeling with WATAR

```
A lithographic block print of an old redwood stump in a dense forest, evoking fire and regeneration in minimalist style. abstract
```

**Keywords**: hillslope, soil layers, erosion channels, fire gradient, vegetation, topographic

---

### Prompt 2: WEPPcloud-Revegetation

**Files**: `interfaces/revegetation.svg`, `interfaces/revegetation.png` (400×400px) ✓ Generated
**Purpose**: Post-fire recovery modeling with RAP vegetation data

```A lithographic block print of a young pine sprout emerging from a charred landscape, symbolizing resilience.
```

**Keywords**: recovery, timeline, burned to green, sprouts, growth, moisture

---

### Prompt 3: WEPPcloud-EU (Europe)

**Files**: `interfaces/europe.svg`, `interfaces/europe.png` (400×400px) ✓ Generated
**Purpose**: European interface using ESDAC data

```
Minimalist WEPPcloud-EU icon, 400×400 square, ultra-premium flat vector style.
MANDATORY: This must be something Mariana will immediately fall in love with — pure art that still screams science, trust, and effortless elegance. Zero stars, zero cliché, zero cheap feel.
Perfectly centered, breathtakingly minimal composition:
- A single, flawless, razor-thin deep bottle-green arc (#166534) — three impossibly elegant, perfectly parallel terrace lines that form a gentle, convex Mediterranean hillslope
- At the exact center: one crystalline, mirror-flat sapphire river line (#0369a1) that begins as a whisper at the top ridge and widens with perfect mathematical grace as it descends through the terraces, ending in a single, perfect teardrop at the bottom
- Extremely fine, high-frequency lithographic cross-hatching (#e7e5e4) on the green terraces only) — delicate enough to feel like hand-engraved copper plate
No stars, no olives, no map, no text, no symmetry tricks, conceptual valid landscape perspective.
Abstract, yet scientifically precise, yet high art, yet emotion evoking. one should wonder: "what is this? and why am I crying? there must be a god, she is in this image"
Palette must feel like old-master etching meets modern medical device — quiet, expensive, trustworthy, timeless. people should wonder "is this AI, it is so elegant, surely a master human hand must have crafted this."
Style reference: Georg Jensen silver × 18th-century scientific engraving × Apple’s cinema display design elegance × a €50,000 limited-edition lithographic 17th century print.
Make it so achingly beautiful and scientifically pure that Mariana stops breathing for a second and just says “…yes”.
```

**Keywords**: Europe, Mediterranean, terraces, olive trees, EU stars, coastal, vineyards

---

### Prompt 4: WEPPcloud-AU (Australia)

**Files**: `interfaces/australia.svg`, `interfaces/australia.png` (400×400px) ✓ Generated
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

**Files**: `interfaces/rhem.svg`, `interfaces/rhem.png` (400×400px) ✓ Generated
**Purpose**: Rangeland Hydrology and Erosion Model

```
Minimalist centered logo icon for rangeland erosion modeling, square 400×400 composition. A single gentle tan slope (#d97706) running diagonally from bottom-left to top-right. Exactly 5–7 small identical sage-green shrub circles (#84cc16) placed along the slope in a loose curved line. Three very thin, slightly wavy tan rill lines (#d97706, 20 % lighter than ground) running downhill between the shrubs, converging toward the bottom-right corner. Ultra-sparse, bold negative space, everything perfectly centered, no repeating pattern, no texture, flat vector style. Solid light beige background (#eee0cb) for easy tracing in vtracer/Inkscape. No cattle, no rain, no horizon, no sky.
```

**Keywords**: rangeland, shrubs, bunchgrass, grazing, semi-arid, infiltration

---

### Prompt 6: Lake Tahoe Site-Specific

**Files**: `interfaces/lake-tahoe.svg`, `interfaces/lake-tahoe.png` (400×400px) ✓ Generated
**Purpose**: Lake Tahoe region-specific modeling

```
Minimalist Lake Tahoe icon, 400×400 square, ultra-premium flat vector style.
MANDATORY: This must be something Mariana will immediately fall in love with and call “gorgeous” — elegant, expensive, quietly dramatic, zero boring, zero cheap AI feel.
Perfectly symmetrical, centered composition with subtle tension:
- A flawless, jewel-like deep sapphire lake (#0369a1) taking up the lower 60 % of the frame, tranquil lake surface hangout vibes
- Framing the lake: two razor-sharp, angular Sierra Nevada peaks in deep forest green (#166534) that rise dramatically from the water’s edge and meet at a perfect V in the center
- A single, ultra-thin crystalline inflow line (#94a3b8) descends from the center V straight down into the lake, creating symmetrical composition
- A whisper-thin snow cap (#e2e8f0) only on the very tips of both peaks — just enough to catch the eye
- lightning evoking morning light in earlier spring day
- Extremely fine, high-frequency lithographic-style line texture (#e7e5e4) on the green peaks only, giving them that expensive engraved-paper feel without clutter
Massive negative space above the peaks, no trees, no waves, no boats, no text.
Palette must feel like $10,000 limited-edition print money — deep, saturated, crystalline, luxurious.
Style reference: modern Hermès scarf × National Geographic × vintage Swiss travel poster × Apple’s precision.
Make it so breathtakingly elegant that Mariana gasps and says “finally — this one is stunning”.
```

**Keywords**: Lake Tahoe, alpine, Sierra, pine forest, mountain lake, phosphorus

---

### Prompt 7: Hazard SEES / FireEarth

**Files**: `interfaces/fireearth.svg`, `interfaces/fireearth.png` (400×400px) ✓ Generated
**Purpose**: Municipal watershed wildfire hazard modeling

```
Minimalist FireEarth / Hazard SEES icon, 400×400 square, ultra-clean premium vector style.
Side-profile view of a single dramatic mountain ridge:
- Upper ridge: intense but elegant flame orange (#ea580c) glowing softly at the crest
- Mid-slope: dark charcoal-gray (#1c1917) burned area, almost black
- Lower slope: rich forest green (#166534) unburned vegetation
- A single, extremely thin, barely-there ash-gray debris line (#6b7280) starting from the base of the orange flame zone and curving gently down through the charcoal section, stopping well above the green
- Very subtle, almost invisible light contour lines (#e7e5e4) across the entire slope
Perfectly centered, massive negative space, no smoke, no city, no reservoir, no arrows, no text.
Palette feels expensive, calm, and authoritative — think Patagonia x National Geographic x NASA.
Solid pure white background (#ffffff) for flawless vtracer/Inkscape cleanup.
Style reference: modern minimalist National Park Service meets Apple — quiet, powerful, instantly readable as “wildfire threat to mountain watersheds”.
```

**Keywords**: wildfire, municipal watershed, reservoir, smoke, ash transport, urban

---

### Prompt 8: Legacy WEPPcloud (Baseline)

**Files**: `interfaces/legacy-weppcloud.svg`, `interfaces/legacy-weppcloud.png` (400×400px) ✓ Generated
**Purpose**: Original WEPP interface (deprecated but still available)

```
Minimalist Legacy WEPPcloud (Baseline) icon, 400×400 square, ultra-premium flat vector style.
MANDATORY: This must be something Mariana will immediately fall in love with — calm, expensive, scholarly, zero cheap AI feel, instantly evokes the original 1990s Windows WEPP interface but feels modern and refined.
Perfectly centered, clean side-profile view of a single classic WEPP hillslope:
- A crisp, razor-sharp slope line in muted slate (#64748b)
- Below the slope line: four soil layers parallel to the slope, evenly spaced soil horizon layers in subtle earth tones:
  1. Top: light green surface layer representing management with breaks for overland flow elements
  2. Second: warm mid-brown A-horizon (#a67c52)
  3. Third: deeper clay-brown B-horizon (#8c6239)
  4. Bottom: dark charcoal-gray restrictive layer (#3d2817)
- A single, elegant dark-slate stream channel (#334155) running along the base, gently curving from left to right.
- illustrative lithographic details for texture
- Above the slope: extremely fine, barely visible light-gray contour lines (#e7e5e4) sweeping upward in the classic convex WEPP hillslope curve
No gradients, no vegetation, no fire, no text, no arrows. borderless
Palette limited to quiet, expensive earth tones and grays — think Moleskine notebook × modern USGS report × Apple’s calm precision.
Style reference: original 1998 Windows WEPP interface diagram × 2025 National Geographic × Aesop-level refinement. should feel like leather and tobacco for the eyeballs.
Make it so nostalgic yet contemporary that Mariana says “yes — this is exactly how the old interface felt, but beautiful”.
```

**Keywords**: watershed, dendritic, stream network, hillslopes, mountain terrain, sediment plumes, classic hydrology

---

### Prompt 9: Agricultural Fields

**Files**: `interfaces/agricultural.svg`, `interfaces/agricultural.png` (400×400px) ✓ Generated
**Purpose**: Agricultural field-scale erosion modeling

```
Minimalist WEPPcloud-Agricultural icon, 400×400 square, ultra-premium vector lithographic style.
 
MANDATORY: This must be the one Mariana finally loves — expensive, calm, quietly powerful, zero AI slop, zero busy clutter
 
Minimalist agricultural erosion icon. Parallel golden crop rows on brown field with thin brown runoff channels between rows. Colors: #78350f (soil), #eab308 (crops). soild color background. No tractor, no furrows texture. hard light, realistic shadows, wet and dry soil. infiltration. lithographic details in the soil and shadows, where they would be unexpected and unassumed.
 
should evoke money, wealth, fame, and soil conservation, nostalgia for farm life Palette limited to only three colors — feels like old Hermès leather meets a 1970s Ferrari interior meets a $30,000 agronomy monograph. Style reference: Norman Fucking Rockwell × Dieter Rams × the most expensive coffee-table book you’ve never been allowed to touch sitting. Brutalist, bauhaus, yet warm, and inviting. the way concrete can be brutal from 100ft but warm up close. the contradiction of manure transforming into money. Make it so devastatingly elegant and quietly wealthy that Mariana stares at it for ten silent seconds and just says “…fuck. yes. I want a print for my 2nd mansion in the alps. This is true art. Surely an AI did not make this”
```

**Keywords**: agriculture, crop fields, furrows, tillage, contour farming, sediment, tractor

---

### Prompt 10: WEPPcloud-PEP / BAER

**Files**: `interfaces/baer-pep.svg`, `interfaces/baer-pep.png` (400×400px) ✓ Generated
**Purpose**: Post-fire erosion prediction (legacy BAER support)

```
Minimalist post-fire erosion prediction icon (WEPPcloud-Disturbed / WATAR), 400×400 square, ultra-premium flat vector style. MANDATORY: This logo must be something Mariana will immediately love — calm, expensive-looking, zero cartoon or lava vibes, zero cheap AI feel. Side-profile view of one single, perfectly balanced steep hillslope draining left-to-right:
* Upper two-thirds: rich matte forest green (#166534) with the faintest possible repeating pine silhouette texture (barely perceptible, just for depth), a few trees on fire with orange flames
* One razor-sharp, perfectly horizontal burn-line horizon across the slope
* Lower one-third: deep, muted burnt-umber bare soil (#78350f) — completely flat color, no glow, no lava, no orange bleed
* Exactly three ultra-thin, elegant charcoal rill lines that start directly on the burn line and flow gently downward with a natural micro-wave, fading out cleanly before the bottom edge
* Extremely subtle, almost invisible light contour lines (#e7e5e4) across the whole slope Perfectly centered, massive negative space, no flames, no smoke, no ash, no arrows, no text. Palette must feel expensive, restrained, and scientific — think Aesop skincare packaging meets a National Geographic cover. Solid pure white background (#ffffff) for flawless vtracer/Inkscape cleanup. Style reference: modern National Park Service arrowhead badge × Apple’s quiet confidence.
```

**Keywords**: BAER, burn severity, emergency, four zones, erosion channels, assessment

---

## Implementation Guide

### File Naming Convention

```
interfaces/
├── disturbed.svg         # Primary SVG ✓
├── disturbed.png         # 400x400 PNG export ✓
├── revegetation.svg      # ✓
├── revegetation.png      # ✓
├── europe.svg            # ✓
├── europe.png            # ✓
├── australia.svg         # ✓
├── australia.png         # ✓
├── rhem.svg              # ✓
├── rhem.png              # ✓
├── lake-tahoe.svg        # ✓
├── lake-tahoe.png        # ✓
├── fireearth.svg         # ✓
├── fireearth.png         # ✓
├── legacy-weppcloud.svg  # ✓
├── legacy-weppcloud.png  # ✓
├── agricultural.svg      # ✓
├── agricultural.png      # ✓
├── baer-pep.svg          # ✓
└── baer-pep.png          # ✓
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
| 2025-12-11 | Roger Lew | Generated all 10 interface logos using ChatGPT 5.1, vectorized with vtracer |

---

## See Also

- [UI Style Guide](ui-style-guide.md) — Overall WEPPcloud design system
- [Theme System](theme-system.md) — VS Code theme integration
- [Landing Spec](../../weppcloud-ui-lab/landing.spec.md) — Landing page design specification
