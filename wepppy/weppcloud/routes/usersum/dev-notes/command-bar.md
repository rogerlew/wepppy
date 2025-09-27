# Command Bar Developer Notes

The command bar provides a keyboard-driven palette for common actions on project pages. Press `:` to activate, type a command, and hit Enter to run it. The logic lives in `wepppy/weppcloud/routes/command_bar/static/command-bar.js` and the matching Flask blueprint is in `routes/command_bar/command_bar.py`.

## Quick Reference
- **Purpose** – Surfacing navigation and utility commands without touching the mouse. `CommandBar.createCommands()` registers the top-level verbs, while `createGetCommandHandlers()` manages the `get` subcommands.
- **Structure** – Every entry supplies a `description` (shown in `:help`) and an `action`. Actions can manipulate the UI directly or call helpers (e.g., `routeGetLoadAvg`). Long-running commands that should keep the palette open must be listed in `STAY_ACTIVE_COMMANDS`.
- **Adding Commands**
  1. Add a new key to the object returned by `createCommands()` (or `createGetCommandHandlers()` for `get` subcommands).
  2. Implement the handler. When network calls are required, follow the existing `route*` helper pattern for clarity and reuse.
  3. Update `SET_HELP_LINES` or other user-facing help text so `:help` remains accurate.
  4. Register a Flask endpoint (usually under `command_bar_bp`) that responds with `{ Success: bool, Content?: {...}, Error?: str }` and wire it into the handler.
- **Routes** – Network-backed actions expect `projectBaseUrl = /runs/<runid>/<config>/`. Concatenate the relative path (for example `command_bar/loglevel`) to reach the matching backend endpoint.

## `data-usersum` Hover Previews
- The browse blueprint (and any other renderer) can wrap parameter names in `<span data-usersum="<parameter>">` to opt into hover previews.
- On the client side, `attachUsersumHover()` listens for `mouseover` events and fetches `/usersum/api/parameter?name=<parameter>` the first time a token is hovered. The short description is cached on the element to avoid redundant requests.
- Because the listener binds at the document root, any template that includes the command bar automatically gains preview support once it emits the `data-usersum` spans.
- This mechanism is parameter-agnostic: the highlighted names can come from management files, soils, or future catalogs as long as they exist in the usersum database.

## Shared Tips
- Use `commandBar.showResult()` to surface diagnostic messages in the output panel instead of `alert()` or console logging.
- When adding network traffic, prefer `fetch()` with `{ cache: 'no-store' }` and consistent JSON responses so UI handlers stay predictable.
- If a command should remain active (e.g., toggling a mode that expects further input), add its verb to `STAY_ACTIVE_COMMANDS` to keep the palette open after execution.
