# Getting started with PowerUser tools

PowerUser access provides advanced tools for custom project configurations,
project troubleshooting and API access. Enable it when you need those workflows;
ordinary project modeling and **More → GL Dashboard** do not require it.

## Enable access

1. Open **Runs → Explore PowerUser access**, or **Profile → PowerUser access**.
2. Review the tool examples and responsibilities, then confirm both statements.
3. Select **Enable PowerUser access**. Approval is immediate; Profile refreshes
   and shows active access with links to your next steps.

If the refresh does not complete, select **Refresh access status** or reload
Profile. Retrying after a connection failure is safe. If your session expired,
sign in again and return to Profile. Do not assume an error means access changed;
check the refreshed status. Existing PowerUsers keep their access, including
accounts created before the current statement. Admin/Root users already have
these tools and do not need to activate PowerUser separately.

## Choose a first task

- **Create a custom configuration:** use **Open Config Builder** on Profile.
  Choose a compatible combination of data and model settings, then create a
  project. PowerUser access does not remove configuration prerequisites.
- **Inspect a project:** use **Go to Runs**, open a project you can access, and
  select **More → PowerUser Panel → Inspect inputs and outputs**. Start by
  reading prepared inputs and available outputs. **Technical details** contains
  saved controller state (NoDb) and component logs for deeper investigation.
- **Troubleshoot a blocked action:** use **Analyze and troubleshoot** in the
  panel. Read [Clearing Locks](clearing-locks.md) before using that action; it is
  for lock-related failures, not routine preparation.
- **Use data from a script:** the **API Token** section of Profile supports
  personal tokens. Follow [Python and R dataset access](profile-jwt-dataset-access-python-r.md)
  and keep tokens secret.

Reload an already-open project after activation so its menu reflects your new
access. The getting-started links remain available on Profile and in the panel.

## Know the boundaries

Access permission, feature maturity and project readiness are different. A
feature may require a particular backend or prepared outputs even when you have
permission. Preview/experimental labels describe maturity, not an access level.
Review inputs, assumptions and outputs before relying on results.

PowerUser does not grant access to unrelated private projects or permission to
operate internal research features. Those features require separate approval.
Request access from [Mariana Dobre](mailto:mdobre@uidaho.edu), naming the
feature and describing your intended use. Sending a request does not grant access.
If you have no internal memberships, the statement remains available under
**Profile → Internal feature access → Internal feature memberships and acknowledgment**;
accepting it alone grants no membership. Assigned memberships that need your
acknowledgment are shown open on Profile.

## Project developer mode

Users with the Dev role can select **Enable developer mode** in the PowerUser
panel on an editable project. This removes the maximum values for upper- and
lower-horizon soil anisotropy; both must still be finite numbers at least 1.
MOFE and hourly water balance/deep seepage must still be enabled. Values above
10 can cause numerical instabilities.

The project displays **Developer mode** while enabled. Other users with normal
permission to edit/run the project can use the expanded values without a Dev
role. Existing PowerUser, Admin or Root membership alone does not grant the
activation action.

There is no off toggle. Clones inherit the source mode. Restoring an archive or
recovering an existing failed fork uses the incoming project state and can
return the project to normal mode; those operations are not blocked by this
setting. A Dev user can enable it again. Enabling mode does not rerun the model
or change historical results. If activation cannot be confirmed, reload the
page to check saved state before retrying.

See the [Project Developer Mode contract (DM-01)](../../../../../docs/schemas/project-developer-mode-contract.md)
for the authoritative activation permissions, project policy, and clone/recovery rules.
