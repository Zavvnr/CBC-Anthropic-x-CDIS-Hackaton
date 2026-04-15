---
description: Code style preferences — neat, readable, well-commented, algorithmically sound, and scalable. Superseded by code-style.md, security.md, and testing.md when they conflict.
---

# Code Preferences

> **Priority note:** Rules in `code-style.md`, `security.md`, and `testing.md` take precedence over this file when they conflict.

---

## 1. Neat Code

- Consistent indentation throughout the file (no mixed styles).
- One blank line between logical blocks; two blank lines between top-level functions or classes.
- No trailing whitespace, no commented-out dead code left behind.
- Keep lines under 120 characters; break long expressions into named sub-expressions.

---

## 2. Easy-to-Understand Variables

- Name variables and functions for what they **mean**, not what they are.
  - `userLoginAttempts` over `cnt`, `x`, or `temp`
  - `isAuthenticated` over `flag` or `b`
  - `fetchUserById` over `getData` or `doStuff`
- Avoid abbreviations unless they are universally understood (`id`, `url`, `err`, `i` in loops).
- Constants in `UPPER_SNAKE_CASE`; booleans prefixed with `is`, `has`, or `can`.

---

## 3. Simple, Purposeful Comments

- Comment **why**, not **what** — the code already says what it does.
- One short line is better than a paragraph. If a comment needs more than two sentences, the code should probably be refactored instead.
- Every public function or class gets a one-line summary (or JSDoc / docstring) describing its purpose.
- Remove comments that restate the code verbatim (e.g., `// increment i` above `i++`).

---

## 4. Best Algorithms

- Choose the right data structure first — an O(1) lookup beats an O(n) loop.
- Prefer built-in language/library implementations over hand-rolled equivalents.
- If a simpler algorithm is fast enough, use it — avoid premature optimization.
- When a non-obvious algorithm is chosen, add a comment with the time/space complexity and the reason for the choice.

---

## 5. Scalable by Default

- Write code that works correctly at 1x load and degrades gracefully at 100x.
- Avoid hard-coded limits, single points of failure, or global mutable state.
- Keep business logic decoupled from infrastructure (DB, HTTP, queue) so either side can be swapped.
- Design functions to accept configuration rather than hard-code it (e.g., pass `maxRetries` as a parameter, not a magic number buried inside).
- Prefer stateless functions and services; isolate state at well-defined boundaries.
