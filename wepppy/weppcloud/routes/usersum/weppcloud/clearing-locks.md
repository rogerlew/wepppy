# Clearing Locks

Use this page when WEPPcloud shows a lock-related error and a Build or Run action will not continue. The standard recovery path is in the run header: **More -> PowerUser Panel -> Analyze and troubleshoot -> Clear Locks**.

## What This Page Helps You Do

- Clear stale locks after an interrupted action.
- Retry blocked build or run actions without editing project files.

## Recommended Workflow

1. Open the affected run page.
2. In the header, open **More**.
3. Select **PowerUser Panel**.
4. Under **Analyze and troubleshoot**, click **Clear Locks**.
5. Return to the main run page and retry the blocked action.

## When To Use This

Use **Clear Locks** only when WEPPcloud reports that a lock is preventing progress (for example after a disconnect, tab close, or interrupted task).

## Limits and Common Mistakes

- Do not use **Clear Locks** as a routine pre-run step.
- If **PowerUser Panel** is not visible, open **Runs → Explore PowerUser access**, or visit **Profile → PowerUser access**. Review the responsibilities and enable access, then reload the project. See the [PowerUser getting-started guide](poweruser-getting-started.md).
- If the same lock error returns immediately after clearing, refresh once and retry. If it still fails, capture the error text and share it with support.

## Related Docs

- [Getting Started with WEPPcloud](getting-started.md)
- [FAQ](faq.md)
