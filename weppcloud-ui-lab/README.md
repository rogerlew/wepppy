# WEPPcloud UI Lab

> React + Vite sandbox for shadcn-driven landings and Deck.GL experiments.

## What lives here?
- Rapid landing page iterations using shadcn/ui, Tailwind, and Aceternity-style interactions.
- Future Deck.GL run viewers that talk to Query Engine APIs before being exported into Flask.
- A clean separation from the core `wepppy` stack so React/NPM complexity stays opt-in.

## Theme Variants

The lab ships with two independent landing page themes:

| Variant | Entry Point | Description |
|---------|-------------|-------------|
| **Dark** (default) | `index.html` | Aurora background, glassmorphism cards, vibrant accent colors |
| **Light** | `index-light.html` | Flat, minimal, governmental aesthetic—clean borders, muted palette |

Both variants share the same data and content but are completely independent codebases. They can be deployed separately or side-by-side.

## Getting started
```bash
cd weppcloud-ui-lab
npm install          # already run once, repeat after pulling updates
npm run dev          # Vite dev server with HMR (serves dark theme at /)
```

To preview the light theme during development:
```bash
# Visit http://localhost:5173/index-light.html
```

### Adding shadcn components
Use the CLI the same way you would in a Next app:
```bash
npx shadcn@latest add button card navigation-menu
```
Components land in `src/components/ui/*` and rely on the shared utilities in `src/lib/utils.ts`.

## Building + exporting to Flask
```bash
npm run build
npm run export:landing
```
Runs `npm run build`, then copies `dist/` into `wepppy/weppcloud/static/ui-lab/`.
From Flask, `current_app.send_static_file('ui-lab/index.html')` will now render the exported bundle.
For the light theme: `current_app.send_static_file('ui-lab/index-light.html')`.

Deck.GL or other scripts can still live inside the React app or be embedded separately—this command just keeps the deployment step one-line.

## Notes
- Tailwind + shadcn were bootstrapped via the official CLI (New York style, neutral base color).
- Path alias `@/*` is preconfigured, so imports like `@/components/ui/button` work out of the box.
- `npm run build` already guards the setup; run it before copying assets to catch Tailwind or TypeScript errors early.
- The light theme removes border-radius globally for a flat, document-like aesthetic suitable for government/institutional contexts.
