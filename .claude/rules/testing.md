---
description: Testing rules Claude must follow — covers unit, integration, UAT, performance, security, and end-to-end testing for every feature.
---

# Testing Rules

## 1. Unit Testing

Every function, method, or module must have unit tests that cover:

- **Happy path** — expected input produces expected output.
- **Edge cases** — boundary values (0, -1, empty string, max int, etc.).
- **Invalid inputs** — `null`, `undefined`, `N/A`, empty arrays, wrong types, malformed data.
- **Error paths** — exceptions, rejected promises, and error return codes.

Rules:
- Each test must target **one responsibility only** — never bundle multiple assertions for unrelated behavior.
- Mock external dependencies (DB, APIs, file system) so tests run in isolation.
- Name tests as: `[function] should [expected behavior] when [condition]`.

---

## 2. Integration Testing

Test the interaction between modules, services, and layers from **top to bottom**:

1. Entry point (route / controller) → service layer → repository / DB → response.
2. Verify data flows correctly across boundaries without loss or corruption.
3. Test with real dependencies where feasible (test DB, sandbox APIs).
4. Cover:
   - Successful chained calls.
   - Failures at each layer (e.g., DB timeout, API 500) and confirm upstream handles them gracefully.
   - Auth and permission gates between layers.

---

## 3. User Acceptance Testing (UAT)

Before any deployment, confirm the feature meets real-world requirements:

- Map each test case to a user story or acceptance criterion.
- Simulate actual user workflows — not just API calls.
- Verify UI feedback, error messages, and success states are correct and readable.
- Sign-off checklist must pass before marking a feature ready for production.

---

## 4. Performance Testing

Measure speed, stability, and scalability under realistic and extreme conditions.

### Required test volumes (apply to every endpoint and input path):

| Volume | Purpose |
|---|---|
| **100 requests** | Baseline — confirm correct behavior under light load |
| **1,000 requests** | Moderate load — identify early degradation |
| **100,000 requests** | Stress — expose caching gaps, rate limiting failures, memory leaks |

### Test types to run:

| Type | What it tests |
|---|---|
| **Load** | Sustained expected traffic — confirm stable response times |
| **Stress** | Beyond max capacity — find the breaking point |
| **Spike** | Sudden traffic burst — confirm recovery without crash |
| **Endurance** | Extended runtime (hours) — detect memory leaks and drift |
| **Volume** | Large data payloads — confirm DB and I/O hold up |
| **Scalability** | Incremental load increase — confirm horizontal/vertical scaling works |

### What to flag:
- Response times that degrade non-linearly as load increases.
- Endpoints that bypass cache and hit the DB on every request at scale.
- Missing or ineffective rate limits discovered only under load.

---

## 5. Security Testing

Run a security pass on every code change:

- **Input validation** — attempt SQL injection, XSS, command injection, and path traversal on every input field.
- **Auth bypass** — attempt to access protected routes without a valid token.
- **Privilege escalation** — attempt to perform actions above the current user's role.
- **Token/secret exposure** — scan responses and logs for leaked credentials, tokens, or PII.
- **Dependency audit** — run `npm audit` / `pip audit` after any dependency change.
- **Rate limit enforcement** — confirm 429 responses are returned and respected at the volumes above.
- **SSRF** — attempt to redirect outbound calls to internal addresses via user input.

---

## 6. End-to-End (E2E) Testing

Simulate complete real-world user workflows from first action to final outcome:

- Cover the critical user paths (sign-up → login → core feature → logout).
- Run against a production-like environment, not mocked services.
- Include:
  - Successful flows.
  - Interrupted flows (drop connection mid-request, session expiry mid-task).
  - Concurrent user scenarios.
- Automate E2E tests to run on every deployment pipeline trigger.

---

## General Reminders

- **Always test everything** — no feature ships without at minimum unit + integration coverage.
- **Test invalid inputs explicitly** — `N/A`, empty string `""`, `null`, `0`, negative numbers, oversized payloads.
- **Use the three volume tiers** (100 / 1,000 / 100,000) on every endpoint to surface caching and rate limiting gaps.
- **Never skip a test type** — if a category is not applicable, state why explicitly and get confirmation.
- **Failing tests block merges** — do not bypass CI test gates.
