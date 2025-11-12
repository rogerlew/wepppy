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
     - 3 columns on desktop, 2 on tablet, 1 on mobile
     - Each logo card contains:
       - Logo image with grayscale filter (`filter: grayscale(100%)`) that transitions to color on hover (`hover:filter-none`)
       - Optional organization name/caption below logo (can be hidden on mobile)
       - Optional link to organization website (logo wraps in anchor tag)
   - **Logo mappings:**
     - **University of Idaho:** 
       - Image: `/weppcloud/static/images/ui-main-horizontal.jpg`
       - Caption: "Go Vandals! University of Idaho"
       - Link: `https://www.uidaho.edu/`
     - **European Union Horizon 2020:**
       - Image: **TODO: Add EU flag/Horizon 2020 logo** (e.g., `eu-horizon-2020-logo.png`)
       - Caption: "WEPPcloud EU has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreement No 101003890."
       - Link: `https://cordis.europa.eu/project/id/101003890`
     - **Swansea University:**
       - Image: `/weppcloud/static/images/Swansea_University_logo.png`
       - Caption: "Gweddw Crefft Heb Ei Dawn - Technical Skill is Bereft Without Culture. Swansea University"
       - Link: `https://www.swansea.ac.uk/`
     - **USDA Forest Service:**
       - Image: `/weppcloud/static/images/usfslogo.png`
       - Caption: "Caring for the land and serving people. Rocky Mountain Research Station"
       - Link: `https://www.fs.usda.gov/rmrs/`
     - **UI Research Computing & Data Services:**
       - Image: `/weppcloud/static/images/RCDS_Logo-horizontal.svg`
       - Caption: "WEPPcloud is proudly hosted by the University of Idaho Research Computing + Data Services."
       - Link: `https://www.uidaho.edu/research/computing`
   - **Styling notes:**
     - Logos should have consistent height (e.g., `h-16` or `h-20`) with `object-contain` to maintain aspect ratio
     - Apply Tailwind filters: `grayscale brightness-0 invert opacity-70` for dark theme integration
     - On hover: `hover:grayscale-0 hover:brightness-100 hover:invert-0 hover:opacity-100`
     - Smooth transition: `transition-all duration-300`
     - Cards have subtle border (`border-white/10`) and background (`bg-slate-900/40`)
     - Generous padding around logos (`p-6` or `p-8`)

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

## TODO

- **Add EU Horizon 2020 logo:** Download official EU flag or Horizon 2020 logo and place in `wepppy/weppcloud/static/images/` (e.g., `eu-horizon-2020-logo.png` or `eu-flag.svg`).
  - Official EU emblem: https://ec.europa.eu/regional_policy/sources/images/emblem_horizontal_colour.jpg
  - Or use EU flag SVG from official sources
