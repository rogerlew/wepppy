# Climate control render test setup

Five tests in `tests/weppcloud/routes/test_pure_controls_render.py` construct
the same climate view model with different selections. Give each case a fresh
model and keep the fields that distinguish the scenario beside its assertions.
The complexity budget is one function-scoped pytest fixture in the test module.
Security impact is none. This package only changes test setup.

Acceptance requires the same ordered pytest cases, assertions, and passing
render results as local master. [Validation tracker](tracker.md)

Closed 2026-11-23 UTC after all 303 focused cases passed.
