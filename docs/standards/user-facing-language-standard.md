# Writing UI and help for people

Applies to user-facing labels, messages, navigation, search text and instructions.
Use this with the ENDUSER authoring guide. This standard guides writing; it does
not authorize changes to access, retention, defaults or other product behavior.

## Start with the person's task

Before drafting, identify the intended reader, what they are trying to do, and
what they need to know to act. Write the question they would ask, such as
“Will my project be deleted?” or “How do I keep my project?” Lead with the answer.
Do not make readers learn the implementation before they can use the product.

Use familiar verbs and concrete objects. Say what changes for the person, not
what the code does. Keep necessary scientific vocabulary: runoff and sediment
yield are useful to this audience; hydration, serialization and TTL are not
needed to manage a project. Expanding an unfamiliar software acronym does not
make the interface understandable. Keep technical identifiers in developer
references unless the user must enter, locate or report them.

## Make controls explain their consequences

- Name the action or setting directly. Honor the operator's approved wording;
  do not substitute a preferred synonym after the wording has been settled.
- Explain a consequential setting beside the control. A separate help article
  supplements the explanation; it must not be required to understand the label.
- Explain what checked and unchecked mean when either could be ambiguous.
- Use the same terms in the control, saved status, confirmation, errors and help.
- Report confirmed results. Distinguish enabled, disabled, unknown and pending
  states. Absence of a date or value is not proof that a setting is disabled.
- On failure, say what is known and what the user can do next. A lost response
  does not prove that the server rejected a change. Do not show success merely
  because the user clicked a checkbox.

| Avoid in ordinary user workflows | Prefer |
| --- | --- |
| Disable TTL Deletion | Disable automatic deletion |
| TTL Deletion: 2026-12-31T00:00:00Z | Automatic deletion is enabled for Dec 31, 2026, 12:00 AM UTC |
| Last Modified, as a substitute for confirmed disabled status | Automatic deletion is disabled |
| Learn More | How to keep your project |
| Usersum | WEPPcloud Help |

These examples preserve the intended meaning; they are not permission to claim
that an unknown state is disabled or that a project is stored forever.

## Put help where people look

Title and organize help by tasks, not internal modules or account hierarchy.
An ordinary project-management task belongs with managing projects, not advanced
operations. Link to the relevant answer beside the action in every relevant
state, including disabled or unknown. Use descriptive link text.

Include natural search phrases in useful headings and sentences. Preserve stable
URLs and identifiers when improving titles. Verify the published navigation and
search results, not just the Markdown source; stale generated indexes can hide
an otherwise correct revision.

## Write the shortest useful instructions

For a small task, give the answer, exact steps and expected confirmation first.
Then explain reversal, limitations and exceptions that affect the user's choice.
Do not force every short help page into a long feature/reference template.
Use actual control labels. When UI changes are in scope, fix confusing labels
and instructions together. For a docs-only task, identify the label problem
instead of inventing a control that does not exist.

Verify feature availability against the accepted product contract and operator
direction. Existing decorators, tests and draft plans describe implementation;
they do not justify inventing or perpetuating a user restriction. Record any
discrepancy rather than rewriting the user promise to match accidental behavior.

## Review the whole task

Before calling the writing complete, check whether the intended user can find
the action, understand its consequence, perform it and recognize success or
failure without developer knowledge. Check the actual rendered UI, help links,
search results, and ordinary-user permissions with scoped tests where relevant.
Test wording against the questions people ask, not just the current labels.

An agent review or passing string assertion does not establish comprehension.
For a usability claim, ask representative users to perform the task and explain
what happened without coaching. Report whether that check was performed; do not
claim users understand merely because the text renders or follows a checklist.
