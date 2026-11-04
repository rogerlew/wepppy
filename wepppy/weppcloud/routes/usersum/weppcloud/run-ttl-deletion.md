# Keep your project from being automatically deleted

## How long are projects saved?

By default, WEPPcloud automatically deletes projects after 90 days without
access. Opening a project restarts that 90-day period. If you need to keep a
project without opening it regularly, disable automatic deletion.

## How do I keep my project?

1. Sign in and open your project.
2. Open **More** in the project header.
3. Check **Disable automatic deletion**.
4. Wait for **Automatic deletion is disabled**, then reload the project to
   confirm that the setting was saved.

Every signed-in user who can access the project can use this setting. No
special account role is required. The same control is available on report pages.

## How do I know whether automatic deletion is enabled?

The project header and your **Runs** list show its status:

- **Automatic deletion is enabled for [date]**: this is the current deletion
  date. Dates are shown in UTC. Accessing the project can move the date later;
  deletion happens during scheduled cleanup, not necessarily at that exact time.
- **Automatic deletion is disabled**: the project's inactivity policy does not
  schedule automatic deletion.
- **Automatic deletion status is unavailable**: WEPPcloud cannot currently
  confirm the setting. This does **not** mean automatic deletion is disabled.
  Open the project and check the setting. The Runs list may take time to update.

**Last Modified** describes changes to the project; it does not confirm whether
it will be deleted. If a save reports an error, reload the page to check the
setting before assuming your change was saved.

## What happens if I turn automatic deletion back on?

Uncheck **Disable automatic deletion**. For an ordinary project, this starts a
new 90-day period. Check the displayed date after saving.

Readonly projects and batch projects are excluded from automatic deletion.
Unchecking this control does not remove those exclusions, so their status can
remain **Automatic deletion is disabled**.

## Can this restore a project that was deleted?

No. This setting cannot undo deletion that has already started or restore deleted
projects. It controls automatic deletion due to inactivity; it does not prevent
someone from manually deleting a project or replace a separate backup.

Older pages and technical documentation call the inactivity timer **TTL**
(time to live). **Disable automatic deletion** is the setting to use when you
want to stop deletion or keep your project without regular access.
