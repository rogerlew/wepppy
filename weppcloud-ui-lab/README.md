# WEPPcloud UI Lab

> React + Vite sandbox for shadcn-driven landings and Deck.GL experiments.

## What lives here?
- Rapid landing page iterations using shadcn/ui, Tailwind, and Aceternity-style interactions.
- Future Deck.GL run viewers that talk to Query Engine APIs before being exported into Flask.
- A clean separation from the core `wepppy` stack so React/NPM complexity stays opt-in.

## Getting started
```bash
cd weppcloud-ui-lab
npm install          # already run once, repeat after pulling updates
npm run dev          # Vite dev server with HMR
```

### Adding shadcn components
Use the CLI the same way you would in a Next app:
```bash
npx shadcn@latest add button card navigation-menu
```
Components land in `src/components/ui/*` and rely on the shared utilities in `src/lib/utils.ts`.

## Building + exporting to Flask
```bash
npm run export:landing
```
Runs `npm run build`, then copies `dist/` into `wepppy/weppcloud/static/ui-lab/`.
From Flask, `current_app.send_static_file('ui-lab/index.html')` will now render the exported bundle.
Deck.GL or other scripts can still live inside the React app or be embedded separately—this command just keeps the deployment step one-line.

## Notes
- Tailwind + shadcn were bootstrapped via the official CLI (New York style, neutral base color).
- Path alias `@/*` is preconfigured, so imports like `@/components/ui/button` work out of the box.
- `npm run build` already guards the setup; run it before copying assets to catch Tailwind or TypeScript errors early.
