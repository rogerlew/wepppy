# Project TTL Deletion

WEPPcloud uses a project time-to-live (TTL) policy to clean up inactive project
data. The **Runs** table shows the current status for each project you can open.

## What TTL Deletion Means

When a project has active TTL deletion, its Runs-table row shows **TTL Deletion**
followed by a timestamp. This is the current scheduled deletion time for that
project. Opening or otherwise accessing an active project refreshes its rolling
TTL, so the displayed timestamp can move later.

The timestamp is specific to that project. Do not treat it as a guaranteed
retention period: project state, readonly status, and service operations can
affect whether a project has an active deletion schedule.

## When You See Last Modified Instead

If **Disable TTL Deletion** is enabled for a project, the Runs table shows
**Last Modified** instead of a TTL deletion time. Readonly and excluded projects,
or older projects without usable TTL metadata, also show Last Modified because
they do not have an active deletion time to display.

## Disabling TTL Deletion

The existing **More → Disable TTL Deletion** control is available only to users
with the required PowerUser, Admin, or Root permission. Turning TTL deletion back
on starts a fresh rolling TTL window. This guide explains the displayed status;
it does not change project retention or restore deleted projects.
