# WP09 Security and Accessibility Review

**Reviewed**: 2026-08-27
**Disposition**: Approved; no unresolved findings

## Security boundary

- Page load makes one bearer-authenticated GET to the read-only availability
  route. It does not request preview details or submit mutation.
- Availability may be visible under run-read authority. Preview and apply still
  require current owner/Admin/Root authority at the server, and WP08 rechecks
  the sanitized actor in the worker.
- The browser submits only the opaque server preview ID and one trigger already
  present in the reviewed additions. It never constructs config values.
- Dynamic section, option, value, source, and revision strings use
  `textContent`, preventing markup execution. Errors use fixed client copy and
  do not surface traceback, token, path, or config content.
- Composite Omni routes are reduced to the top-level run for config resolution,
  enqueue single-flight identity, and worker mutation. Existing auth already
  uses the same top-level authorization identity.

## Accessibility boundary

- The update notice is a native button and the digest warning is a nonblocking
  status. Both remain absent from navigation when unavailable.
- The modal has an accessible name and description, canonical focus trap and
  focus return, an explicitly labelled close button, and keyboard-operable
  native controls.
- The complete additions table has a caption and scoped headers. Horizontal
  overflow preserves content at narrow viewport widths.
- Preview/job state uses a polite live region. Actionable errors use a
  focusable alert, and completion moves focus to its status message.
- Apply is disabled before review and during submission; duplicate activation
  cannot enqueue a second request from the controller.

## Residual risk

Job polling uses the canonical open status route and a one-second interval. A
browser closing the modal does not cancel the already authorized job; this is
intentional because the worker and project lock own lifecycle integrity. The
feature remains default-off pending Forest and production promotion packages.
