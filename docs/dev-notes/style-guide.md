# Developer Style Guide

> **See also:** [AGENTS.md](../../AGENTS.md) for Code Style and Conventions section.

## Core Principles
- **Clarity First**: Prefer direct, in-place logic over indirection. Inline simple expressions instead of hiding them behind helpers when there is only one call site.
- **Avoid Phantom Flexibility**: Do not add optional parameters or extension points until there is a proven need. Dead code paths mislead reviewers and future maintainers.
- **Simplicity Over Cleverness**: Reach for the least complex structure that conveys the intent. Fewer moving parts mean fewer assumptions to check when reading the code.
- **Locality of Reference**: Keep related operations together. When setting up, mutating, and acting on state, keep those steps visible in the same function unless there is strong reuse pressure.
- **Explicit > Implicit**: Derive identifiers, file paths, and configuration inline when they are formulaic. Naming factories or helpers should only exist when multiple flows truly depend on them.

## Ergonomics Guidelines
- **Readable Signatures**: Method signatures should reflect what callers can actually influence. Remove unused arguments rather than parking them "for later".
- **Progressive Disclosure**: Document or link to background context only when necessary. Default to self-explanatory code so engineers need fewer jumps.


## Review Checklist
- Is there an unnecessary helper or abstraction layer that hides trivial logic?
- Are all parameters, return values, and timestamps actually used by callers?
- Is the control flow easy to follow without jumping across files?
- Would a future reader understand why each branch exists within a minute?

If any answer is “no”, simplify before merging.
