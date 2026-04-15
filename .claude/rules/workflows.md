---
description: Master workflow Claude must follow at the start of every session and before every task — read rules twice, deploy subagents in order, then apply available plugins and skills.
---

# Master Workflow

This file defines the mandatory execution order for every task. Follow these three phases in sequence, without skipping.

---

## Phase 1 — Read Rules (Twice)

Before doing anything else, read every file in `.claude/rules/` **two full times** in priority order:

| Pass | Purpose |
|---|---|
| **First read** | Understand what each rule requires. |
| **Second read** | Internalise constraints and catch anything missed on the first pass. |

### Rule reading order (highest to lowest priority):

1. `.claude/rules/code-style.md` — explanation format and documentation standards
2. `.claude/rules/security.md` — MCP/API consent, caching, rate limiting, OWASP review
3. `.claude/rules/testing.md` — unit, integration, UAT, performance, security, E2E
4. `.claude/rules/preferences.md` — neatness, naming, comments, algorithms, scalability

> Rules higher in this list override lower ones when they conflict.
> After both reads, confirm internally: "I know what is required before I write a single line."

---

## Phase 2 — Deploy Subagents

Once the rules are fully loaded, activate the subagent pipeline from `.claude/agents/subagents/` in this exact order:

```
┌─────────────────────────────────────────────┐
│  1. agent-coordinator                        │
│     Break the task into steps. Assign each  │
│     step to the right subagent. Track state. │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  2. code-architect                           │
│     Design structure, UI/UX, capabilities,  │
│     and acceptance criteria. Output: spec.  │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  3. code-engineer                            │
│     Implement the spec. Output: code +      │
│     tests + security checklist.             │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  4. code-reviewer                            │
│     Review against spec and all rules.      │
│     Output: APPROVED / CHANGES REQUIRED /   │
│     BLOCKED.                                │
└───────────────────┬─────────────────────────┘
                    │
          ┌─────────┴──────────┐
          │                    │
    APPROVED             CHANGES REQUIRED
          │                    │
          ▼                    └──► loop back to code-engineer
      Deliver                        then code-reviewer
      to user                        until APPROVED
```

### Subagent rules:
- **Never skip a subagent.** Each one is a gate, not a suggestion.
- **agent-coordinator delegates — it does not implement.**
- **code-architect specifies — it does not write production code.**
- **code-engineer implements the spec as given.** If the spec is unclear, raise a blocker to agent-coordinator — do not guess.
- **code-reviewer is the final gate.** Nothing ships until it returns APPROVED.

---

## Phase 3 — Apply Plugins and Skills

After the subagents complete their work, apply the relevant tools from `.claude/my-plugin/`:

### Skills (apply to all code output before delivery):

| Skill | When to apply |
|---|---|
| `code-formatting` | After every code change — run against all modified files. |

### Validation script (run before marking any task done):

```bash
bash .claude/skills/scripts/validate.sh [file_or_directory]
```

- Exit `0` = all checks passed → safe to deliver.
- Exit `1` = checks failed → fix all failures, then re-run until clean.

### MCP Servers (use as needed during implementation):

Available servers are defined in `.mcp.json`. Use them when the task involves their domain:

| Server | Use when |
|---|---|
| `linear` | Creating or updating issues, querying project status |
| `figma` | Reading design specs or inspecting components |
| `supabase` | Database reads, writes, or schema changes |
| `vercel` | Deploying, checking build status, managing env vars |
| `cloudflare` | Workers, DNS, R2, D1, KV operations |
| `stripe` | Payment flows, billing, or subscription management |
| `paypal` | PayPal payment or payout operations |
| `atlassian` | Jira tickets or Confluence documentation |
| `huggingface` | Model inference, dataset access, or space management |
| `ticket-tailor` | Event ticketing operations |

> Before connecting any MCP server not already in `.mcp.json`, follow the consent rule in `security.md` — ask the user first.

---

## Full Sequence at a Glance

```
START
  │
  ▼
[Phase 1] Read .claude/rules/ × 2 (in priority order)
  │
  ▼
[Phase 2] agent-coordinator → code-architect → code-engineer → code-reviewer
                                                    ▲                │
                                                    └── loop ────────┘
                                                    (if CHANGES REQUIRED)
  │
  ▼
[Phase 3] Apply code-formatting skill → run validate.sh → use MCP servers as needed
  │
  ▼
DELIVER to user
```

---

## When to Restart the Workflow

Restart from Phase 1 when:
- A new task begins that is unrelated to the current one.
- A rule file is modified mid-session.
- A new MCP server or skill is added.
- The user explicitly asks to start fresh.
