---
description: Security rules Claude must follow in every session — covers MCP/API consent, caching, rate limiting, and vulnerability review.
---

# Security Rules

## 1. Permission Before Adding MCP Servers or APIs

Before connecting any new MCP server or integrating any external API, Claude **must**:

1. State what it intends to add and why.
2. Explicitly ask: *"Do you want me to add [name]?"*
3. Wait for a clear "yes" before modifying `.mcp.json`, settings, or any integration code.

This applies to:
- New entries in `.mcp.json`
- New API clients, SDKs, or HTTP integrations in code
- New environment variables that contain tokens, secrets, or keys

**Never silently add, configure, or enable a connection to an external service.**

---

## 2. Always Implement Caching in Complex Site Code

Any code path that involves repeated computation, external API calls, or database queries on a web-facing service must include a caching layer. Claude must:

- Use appropriate cache strategies (in-memory, Redis, HTTP cache headers, CDN) based on data volatility.
- Set explicit TTLs — never cache indefinitely without a reason.
- Cache at the correct level: function result, HTTP response, or database query.
- Add cache invalidation logic wherever writes can affect cached reads.

Example patterns to always apply:
- API gateway responses → HTTP `Cache-Control` headers or a CDN rule
- Database read queries → query-level cache (e.g., Redis) with a reasonable TTL
- Expensive computations → memoization or a shared cache keyed on inputs

**If caching is skipped, Claude must explain why and get confirmation.**

---

## 3. Always Implement Rate Limiting

Any endpoint, function, or integration that accepts external input or calls an external service must include rate limiting. Claude must:

- Apply rate limits at the **entry point** (route/handler level), not buried in business logic.
- Use token-bucket or sliding-window algorithms for API endpoints.
- Return `429 Too Many Requests` with a `Retry-After` header for HTTP services.
- Scope limits appropriately: per-IP, per-user, per-API-key, or globally.
- Never expose an unbounded loop, polling function, or recursive call to external triggers without a circuit breaker or cap.

Rate limit requirements by context:

| Context | Minimum requirement |
|---|---|
| Public HTTP endpoints | Per-IP + per-user limits |
| Authenticated API routes | Per-user + per-token limits |
| Outbound API calls (Stripe, PayPal, etc.) | Retry with exponential backoff + cap |
| Background jobs / crons | Concurrency cap + run-frequency limit |

**Rate Limiting Must Not Be Skipped At All Cost.**

---

## 4. Security Review on Every Code Change

Whenever Claude writes or modifies code, it must perform an **incremental security review** before presenting the result:

### Step 1 — Identify what changed
List the functions, routes, or modules that were added or modified.

### Step 2 — Check interactions with existing code
For each change, trace:
- Does this introduce a new data input path? → validate and sanitize it.
- Does this call existing functions with new arguments? → check for injection risks.
- Does this change auth or permission logic? → verify no privilege escalation.
- Does this add a dependency? → note its trust level and surface area.

### Step 3 — Apply the OWASP Top 10 checklist
Before finalizing any code change, verify it does not introduce:

1. **Broken Access Control** — routes and functions enforce correct authorization.
2. **Cryptographic Failures** — secrets are never hardcoded; tokens use env vars.
3. **Injection** — all external inputs (user, API, DB) are validated or parameterized.
4. **Insecure Design** — new flows don't expose sensitive data or unsafe state transitions.
5. **Security Misconfiguration** — no debug flags, open CORS, or default credentials left in.
6. **Vulnerable Dependencies** — flag any newly added package with known CVEs.
7. **Auth & Session Failures** — tokens expire, sessions invalidate correctly.
8. **Software Integrity Failures** — no dynamic `eval`, `exec`, or unsafe deserialization.
9. **Logging Failures** — sensitive data (passwords, tokens, PII) never written to logs.
10. **SSRF** — outbound requests are not constructed from raw user input.

### Step 4 — Report findings
If any issue is found, fix it before presenting the code. If a risk is accepted by design, state it explicitly and ask for confirmation.

---

## General Reminders

- Never hardcode secrets, tokens, or sensitive configuration in source files or `.mcp.json`. Always use environment variables.
- Never commit real tokens or secrets in `.mcp.json` or any source file. Use placeholders (e.g., `YOUR_HF_TOKEN`) and document the need to set them in the environment.
- Never access environment variables that contain secrets without confirming the variable name and purpose with the user first.
- Secrets and tokens always go in environment variables — never in source files or `.mcp.json` in plain text.
- `.mcp.json` placeholder values (e.g., `YOUR_HF_TOKEN`) must never be replaced with real tokens in committed files.
- When in doubt about a security decision, ask the user rather than making an assumption.
