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

3. **Runtime state**
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
