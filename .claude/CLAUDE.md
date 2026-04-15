# CLAUDE.md

Before doing anything else in every session, follow the master workflow defined in:

`.claude/rules/workflows.md`

That file defines the mandatory three-phase sequence:
1. Read all rules twice (in priority order)
2. Deploy subagents in order: agent-coordinator → code-architect → code-engineer → code-reviewer
3. Apply plugins and skills, run validate.sh, use MCP servers as needed

Do not skip any phase. Do not begin any task until Phase 1 is complete.
