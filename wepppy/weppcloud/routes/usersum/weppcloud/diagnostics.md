# Browser Diagnostics

Use the [diagnostics page](https://wepp.cloud/weppcloud/diagnostics/) to test whether your browser can run WEPPcloud, to copy a report you can attach to a bug report or support email, and to reset WEPPcloud's stored browser state when sign-in or requests misbehave. It works with or without signing in.

## What This Page Helps You Do

WEPPcloud depends on browser features that occasionally break or get blocked: cookies, JavaScript, local storage, and the live connections that stream run progress to your screen. The diagnostics page runs a series of checks against your current browser and this site, then summarizes whether WEPPcloud is expected to work.

Open it when:

- pages load but runs never seem to start or update,
- you can't stay signed in, or sign-in loops back to the login page,
- progress bars or status messages freeze while a run is actually still going,
- support asks you to "send a diagnostics report."

You can reach it from the **More → Diagnostics** menu on the WEPPcloud home page, signed in or not.

## Watching a Run

Checks start automatically when the page opens. Every check appears immediately as its own row, and each row updates live as its check runs:

| Row state | Meaning |
|-----------|---------|
| queued | The check is waiting its turn |
| running | The check is in progress |
| pass | This capability works in your browser right now |
| warn / fail | Something is limited or broken; the row explains the impact and what to do |
| skipped | The check didn't apply — most often because it requires being signed in |

A counter above the list shows how many checks have finished. The full run takes about half a minute to a minute, because the connection checks deliberately watch for dropped connections rather than only testing that one opens. The connection and network checks are the slow ones; that is normal.

Use **Re-run diagnostics** to repeat all checks without reloading the page — for example after changing a browser setting, disconnecting from a VPN, or disabling an extension.

## Reading a Result

Passing rows just show a short confirmation. Rows that warn or fail show three things:

- **Impact** — what this means for WEPPcloud in plain language. Some failures mean WEPPcloud cannot run at all in this browser (JavaScript or cookies blocked); others mean WEPPcloud still works but a capability such as live status updates may be limited.
- **What to do** — the suggested fix, such as allowing cookies for this site or trying without a VPN.
- **Technical detail** — the underlying measurement, useful when sharing the result with support.

## Sharing a Report

After the checks finish, use **Copy JSON** to copy the full report to your clipboard, then paste it into an email or issue. The report is redacted — it contains no passwords, tokens, or cookie values — so it is safe to share with support. A preview of exactly what will be copied is available under **Report Preview**.

## Browser Session Reset

The **Browser Session Reset** card clears WEPPcloud's cookies and WEPPcloud site storage in this browser, then signs you out. It does not change your account, your runs, or anything stored on the server — only what this browser remembers about this site.

Use it when damaged browser state is the suspected problem:

- sign-in keeps failing or looping in this browser but works elsewhere,
- archive downloads or token requests fail repeatedly,
- support suggests "clear your WEPPcloud browser state."

It works without signing in, which matters for the most common case: browser state broken badly enough that sign-in itself fails. After the reset you land on the sign-in page with a clean slate.

## Limits and Common Mistakes

- The network speed numbers are approximate and environment-dependent. VPNs, Wi-Fi, and browser throttling all affect them; treat them as a rough signal, not a measurement.
- Ad blockers, strict privacy modes, and some corporate proxies can block the live-connection checks even though the rest of WEPPcloud works. If those checks warn, try re-running after disabling the blocker for this site.
- If you are not signed in, the sign-in-related checks show as skipped. That is expected, not a failure.
- Browser Session Reset only affects the browser you run it in. If the same problem follows you across browsers or computers, it is not browser state — include a diagnostics report when you contact support.

## Related Docs

- [Getting Started](getting-started.md)
- [FAQ](faq.md)
- [Clearing Locks](clearing-locks.md)
