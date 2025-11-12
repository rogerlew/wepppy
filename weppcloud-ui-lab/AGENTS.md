# AGENTS.md — weppcloud-ui-lab

## Context & Hostname

- `forest.local` **is** `wc.bearhive.duckdns.org`. You are on the homelab dev box when inside this repo. All paths like `/wc1/...` refer to the same filesystem regardless of the hostname.

## Project Structure

- Vite + React (TypeScript) lives under `weppcloud-ui-lab/`.
- Build workflow:
  - `npm run build`
  - `npm run export:landing` (builds + copies to `wepppy/weppcloud/static/ui-lab/`)
- Static assets served by Flask `/landing/` route via `runid-locations.json` + the exported bundle.

## Playwright MCP

- Playwright CLI is installed (`npx playwright ...`). Use it for visual verification (e.g. scroll/pinning checks) in addition to the MCP commands in the Codex CLI.
- When verifying scroll states, explicitly scroll via `page.evaluate(() => window.scrollBy(...))` or use the CLI `--wait-for-timeout`.

## shadcn MCP

- Project already initialized with shadcn (`components.json` present). Use `npx shadcn@latest add <component>` when adding UI primitives.
- Lucide icon set (e.g., `Zap`) is available through shadcn.

## Help Section Assets

- YouTube card uses `/weppcloud/static/images/youtube.png`.
- GitHub icon uses inline SVG (see `renderHelpIcon()` in `src/App.tsx`).

## Map Data Notes

- `/landing/run-locations.json` now rebuilds from `/geodata/weppcloud_runs/access.csv`. The `access.csv` is copied from production for development purposes. Don't overwrite `access.csv` or modify `compile_dot_logs.py`

