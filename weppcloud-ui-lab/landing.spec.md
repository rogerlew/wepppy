# WEPPcloud Landing Spec

## Sections

1. **Quick Links Hero (Aurora)**
   - Full-height (`min-h-[100svh]`) aurora background using `AuroraBackground`.
   - Copy: eyebrow `WEPPcloud`, headline typewriter `"Watershed intelligence for response teams"`, supporting quick-links paragraph.
   - Buttons: Interface, Docs, Research, Login/Runs (auth aware).
   - Content offset `pt-[600px]` to sit within aurora gradient.

2. **Run Atlas Hero (Map)**
   - Eyebrow: `Run atlas`
   - Title: `Explore Active WEPPcloud Projects`
   - Subtitle: `Every WEPPcloud run ... platform.` (same as legacy landing).
   - Metric cards (unique runs, total hillslopes, latest access) displayed beneath copy.
   - Entire section pins while scrolling using `MAP_PIN_OFFSET` (currently 800px):
     - `section#map` height: `calc(100vh + offset)`
     - `.map-pin-wrapper` fills the section; `.map-pin-container` is `position: sticky; top: 0`
     - Run Atlas copy/metrics and the Deck.GL map remain visible throughout the pinned duration.
   - Deck.GL now renders immediately (no lazy observer), showing scatter/text layers + legend overlay, control drawer, status bubble, and on-canvas Ctrl+scroll tooltip.

3. **Help / Resources**
   - Eye-level cards beneath the pinned map showcasing self-serve resources.
   - **Quick Start:** Card linking to `https://doc.wepp.cloud/QuickStart.html` with the Lucide `Zap` icon.
   - **WEPPcloud YouTube:** Card linking to `https://www.youtube.com/@fswepp4700` with thumbnail from `static/images/youtube.png`.
   - **wepppy GitHub:** Card linking to `https://github.com/rogerlew/wepppy` using the provided GitHub SVG icon.
   - Layout: three responsive cards (stacking on mobile) with short descriptions and CTA links.

4. **Points of Contact**
   - Grid of contact cards (2 columns, responsive) showcasing the WEPPcloud team.
   - **Roger Lew** (Icon: `Server`)
     - Title: WEPPcloud DevOps Architect, Associate Research Professor
     - Institution: University of Idaho
     - Email: rogerlew@uidaho.edu
     - Expertise: WEPPcloud, WEPP input and outputs, data pipelines and analysis
   - **Mariana Dobre** (Icon: `Settings`)
     - Title: Assistant Professor
     - Institution: University of Idaho
     - Email: mdobre@uidaho.edu
     - Expertise: Hydrology, Soil Science, Calibration, Forests
   - **Pete Robichaud** (Icon: `Flame`)
     - Title: Research Engineer
     - Institution: USDA Forest Service, Rocky Mountain Research Station
     - Email: peter.robichaud@usda.gov
     - Expertise: Forest, WEPP, Post-fire erosion modeling, Ash Transport
   - **Anurag Srivastava** (Icon: `CloudRain`)
     - Title: Research Scientist
     - Institution: University of Idaho
     - Email: srivanu@uidaho.edu
     - Expertise: WEPP model, Hydrology, Soil Erosion, Forest, Agriculture, Climate datasets and processing for WEPP
   - **Erin Brooks** (Icon: `Sprout`)
     - Title: Professor
     - Institution: University of Idaho
     - Email: ebrooks@uidaho.edu
     - Expertise: Landscape hydrology, precision agriculture, nutrient cycling and transport, water quality, erosion
   - **Brian (Scott) Sheppard** (Icon: `FileText`)
     - Title: Research Hydrologist
     - Institution: USDA Forest Service, Rocky Mountain Research Station
     - Email: brian.sheppard@usda.gov
     - Expertise: Hydrology, fire response modeling

5. **Affiliations and Collaborators**
   - Dark section (`bg-[#020617]` or similar) with centered eyebrow, heading, and subtitle.
   - **Eyebrow:** `Collaborators`
   - **Heading:** `Affiliations and Collaborators`
   - **Subtitle:** `WEPPcloud is made possible through collaborative partnerships across research institutions, government agencies, and international funding programs.`
   - Logo grid (responsive, centered, max-width container):
     - 4 columns on desktop, 2 on tablet, 1 on mobile
     - Each logo card contains:
       - Logo image with grayscale filter (no hover colorization)
       - Organization caption below logo
       - Link to organization website (logo wraps in anchor tag)
   - **Logo mappings:**
     - **University of Idaho:** 
       - Image: `/weppcloud/static/images/University_of_Idaho_logo.svg`
       - Caption: "Go Vandals! University of Idaho"
       - Link: `https://www.uidaho.edu/`
     - **Swansea University:**
       - Image: `/weppcloud/static/images/Swansea_University_logo.png`
       - Caption: "Gweddw Crefft Heb Ei Dawn - Technical Skill is Bereft Without Culture"
       - Link: `https://www.swansea.ac.uk/`
     - **USDA Forest Service:**
       - Image: `/weppcloud/static/images/Logo_of_the_United_States_Forest_Service.svg`
       - Caption: "Caring for the land and serving people. Rocky Mountain Research Station"
       - Link: `https://www.fs.usda.gov/rmrs/`
     - **UI Research Computing & Data Services:**
       - Image: `/weppcloud/static/images/RCDS_Logo-horizontal.svg`
       - Caption: "Proudly hosted by the University of Idaho Research Computing + Data Services"
       - Link: `https://www.uidaho.edu/research/computing`
     - **Rangeland Analysis Platform:**
       - Image: `/weppcloud/static/images/rapIconSmall.png`
       - Caption: "Big data for big landscapes - combining satellite imagery with thousands of on-the-ground vegetation measurements"
       - Link: `https://rangelands.app/`
     - **Michigan Technological University:**
       - Image: `/weppcloud/static/images/michigan-tech-logo-full-yellow.svg`
       - Caption: "Tomorrow needs Michigan Tech - R1 flagship technological research university"
       - Link: `https://www.mtu.edu/`
     - **Washington State University:**
       - Image: `/weppcloud/static/images/Washington-State-University-Logo.png`
       - Caption: "World-class research university dedicated to solving problems and improving lives"
       - Link: `https://www.wsu.edu/`
   - **Styling notes:**
     - Logos have consistent height (`h-20`) with `object-contain` to maintain aspect ratio
     - Apply Tailwind filters: `grayscale invert opacity-60 contrast-125` for dark theme integration
     - No hover colorization (logos stay filtered)
     - Cards have subtle border (`border-white/10`) and background (`bg-slate-900/40`)
     - Generous padding around logos (`p-8`)

6. **Sponsors**
   - Dark section (`bg-[#050714]` or similar darker than affiliations) with centered eyebrow, heading, and subtitle.
   - **Eyebrow:** `Funding`
   - **Heading:** `Sponsors`
   - **Subtitle:** `WEPPcloud development is supported by grants from federal agencies, international research programs, and scientific funding bodies.`
   - Logo grid (responsive, centered, max-width container):
     - Same styling as Affiliations section
     - 4 columns on desktop, 2 on tablet, 1 on mobile
     - Each logo card contains:
       - Logo image with same grayscale filter as affiliations
       - Funding acknowledgment caption below logo
       - Optional link to funding program website
   - **Logo mappings:**
     - **NSF Idaho EPSCoR:**
       - Image: **MISSING** - Need NSF logo (e.g., `nsf-logo.svg` or `nsf-epscor-logo.png`)
       - Caption: "This work was made possible by the NSF Idaho EPSCoR Program and by the National Science Foundation under award number IIA-1301792."
       - Link: `https://www.nsf.gov/` or `https://www.idahoepscor.org/`
     - **USDA NIFA:**
       - Image: `/weppcloud/static/images/USDA_logo.png`
       - Caption: "This work is supported by AFRI program [grant no. 2016-67020-25320/project accession no. 1009827] from the USDA National Institute of Food and Agriculture."
       - Link: `https://www.nifa.usda.gov/`
     - **UKRI / NERC:**
       - Image: `/weppcloud/static/images/ukri-nerc-logo-600x160.png` (combined logo preferred) or `/weppcloud/static/images/UKRI-Logo_Horiz-RGB.png`
       - Caption: "The Wildfire Ash Transport And Risk estimation tool (WATAR) was made possible with funding provided by UK NERC Grant NE/R011125/1 and European Commission (H2020 FirEUrisk project no. 101003890)."
       - Link: `https://www.ukri.org/councils/nerc/`
     - **NASA Western Water Applications Office:**
       - Image: `/weppcloud/static/images/nasa_logo.svg`
       - Caption: "The revegetation module in WEPPcloud was supported by NASA's Western Water Application Office (WWAO)."
       - Link: `https://wwao.jpl.nasa.gov/`
   - **Styling notes:**
     - Same filter as Affiliations: `grayscale invert opacity-60 contrast-125`
     - No hover effects (keep static)
     - Cards match Affiliations styling for consistency
     - Captions may be longer (funding acknowledgments) so ensure adequate spacing

7. **Contributors**
   - Dark section (`bg-[#030712]` or similar) with centered eyebrow, heading, and subtitle.
   - **Eyebrow:** `Team`
   - **Heading:** `Contributors`
   - **Subtitle:** `WEPPcloud is the result of collaborative efforts from researchers, engineers, and scientists across multiple institutions.`
   - Simple badge/pill design (not cards):
     - Responsive flex layout with wrapping (`flex-wrap`)
     - Contributors displayed as rounded pills/badges
     - Each badge contains just the contributor's name
     - Badges should be compact and flow naturally
     - Centered container with max-width
   - **Contributors list (alphabetical by last name):**
     - Marta Basso
     - Erin Brooks
     - Chinmay Deval
     - Mariana Dobre
     - Stefan Doerr
     - Helen Dow
     - William Elliot
     - Jim Frakenberger
     - Roger Lew
     - Mary E. Miller
     - Jonay Neris
     - Pete Robichaud
     - Cristina Santin
     - Brian (Scott) Sheppard
     - Anurag Srivastava
   - **Implementation notes:**
     - Use a simple JavaScript array of strings for easy maintenance:
       ```typescript
       const CONTRIBUTORS = [
         'Marta Basso',
         'Erin Brooks',
         // ... etc
       ]
       ```
     - No images, no links - just names in badges
     - Adding new contributors should be as simple as adding a string to the array
   - **Styling notes:**
     - Badges: `rounded-full px-4 py-2 text-sm` 
     - Background: `bg-slate-800/60` or similar subtle dark background
     - Text: `text-slate-200`
     - Border: optional subtle border `border border-white/10`
     - Spacing: `gap-3` between badges
     - Layout: `flex flex-wrap justify-center items-center`
     - Container: `max-w-5xl mx-auto`
     - Minimal animation: optional fade-in on viewport entry

### Runtime state
   - Flask injects `window.__WEPP_STATE__` with `user.is_authenticated`, email, name.
   - React reads state on mount to toggle nav button text/link.

## Animations & Interactions

- Framer Motion handles hero copy/nav fade-in, metric block/map slide-up.
- Typewriter effect animates hero headline (`speed=2`, `delay=200ms`).
- Aurora overlay is fixed to the viewport (full-screen `fixed` layer) and fades out based on scroll progress (fully transparent after ~0.6 viewport height).
- Map section pins during scroll; map renders immediately, and scroll-wheel zoom requires holding `Ctrl` to avoid hijacking page scroll.
- Help cards animate in with Framer Motion (fade/slide) after the pinned map releases.

## Build/export

- `npm run export:landing` builds Vite bundle and copies to `wepppy/weppcloud/static/ui-lab/`.
- Flask `landing()` route injects `__WEPP_STATE__` before serving `index.html`.

8. **Attributions and Data Sources**
   - Final section at bottom of page with dark background (`bg-[#020617]` or similar).
   - Two subsections side-by-side on desktop, stacked on mobile.
   - **Eyebrow:** `Credits`
   - **Heading:** `Attributions and Data Sources`
   - **Subtitle:** `WEPPcloud leverages open data, research-quality datasets, and mapping services from partners worldwide.`
   
   **Subsection A: Attributions**
   - **Subheading:** `Map Services`
   - **Content:** Plain text attribution with inline links
     - "Map baselayers provided by [Google](https://www.google.com/maps) (Terrain, Satellite) and [OpenStreetMap](https://www.openstreetmap.org/) contributors."
   - **Styling notes:**
     - Simple paragraph text with subtle styling
     - Links styled consistently with rest of page (`text-sky-300 hover:text-sky-200`)
     - Compact, not card-based
   
   **Subsection B: Data Sources**
   - **Subheading:** `Regional Data Documentation`
   - **Content:** List of links to regional data documentation pages
     - **United States:** https://doc.wepp.cloud/us-data.html
     - **Europe:** https://doc.wepp.cloud/eu-data.html
     - **Australia:** https://doc.wepp.cloud/au-data.html
     - **Earth:** https://doc.wepp.cloud/earth-data.html
   - **Styling notes:**
     - Simple list layout (not card-based)
     - Each region name is a link to its data documentation page
     - Links styled consistently (`text-sky-300 hover:text-sky-200`)
     - Optionally use globe/map icons next to region names (e.g., Lucide `Globe`, `MapPin`)
     - Vertical list or horizontal flex layout depending on space
   
   **Layout notes:**
   - Desktop: two-column grid (Attributions left, Data Sources right)
   - Mobile: stack vertically (Attributions on top, Data Sources below)
   - Container: `max-w-5xl mx-auto`
   - Padding: generous spacing (`py-20`)
   - Text styling: `text-slate-300` for body, `text-white` for subheadings
   - Keep design lightweight - this is informational, not promotional

````
