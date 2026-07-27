# Browser Diagnostics

Use the [diagnostics page](https://wepp.cloud/weppcloud/diagnostics/) to test whether your browser can run WEPPcloud, and to copy a report you can attach to a bug report or support email. It works with or without signing in.

## What This Page Helps You Do

WEPPcloud depends on browser features that occasionally break or get blocked: cookies, JavaScript, local storage, and the live connections that stream run progress to your screen. The diagnostics page runs a series of checks against your current browser and this site, then summarizes whether WEPPcloud is expected to work.

Open it when:

- pages load but runs never seem to start or update,
- you can't stay signed in, or sign-in loops back to the login page,
- progress bars or status messages freeze while a run is actually still going,
- support asks you to "send a diagnostics report."

## How To Read the Results

Each check reports one of a few states:

| State | Meaning |
|-------|---------|
| pass | This capability works in your browser right now |
| warn / fail | Something is limited or broken; the check explains the impact and suggests a fix |
| skipped | The check didn't apply — most often because it requires being signed in |

Failures differ in how much they matter. Some mean WEPPcloud cannot run at all in this browser (for example, JavaScript or cookies blocked). Others mean WEPPcloud will still work but a convenience may be limited — most commonly the live status updates during a run. The check text tells you which situation you are in and what to try.

The full run takes about half a minute to a minute, because the connection checks deliberately watch for dropped connections rather than only testing that one opens.

## Sharing a Report

After the checks finish, use **Copy JSON** to copy the full report to your clipboard, then paste it into an email or issue. The report is redacted — it contains no passwords, tokens, or cookie values — so it is safe to share with support.

## Limits and Common Mistakes

- The network speed numbers are approximate and environment-dependent. VPNs, Wi-Fi, and browser throttling all affect them; treat them as a rough signal, not a measurement.
- Ad blockers, strict privacy modes, and some corporate proxies can block the live-connection checks even though the rest of WEPPcloud works.
- If you are not signed in, the sign-in-related checks show as skipped. That is expected, not a failure.

## Related Docs

- [Getting Started](getting-started.md)
- [FAQ](faq.md)
- [Clearing Locks](clearing-locks.md)
