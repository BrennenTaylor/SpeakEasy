# QA Steps Documentation Design

> Short design for a small documentation/process change.

**Intent:** Make user-runnable QA steps a durable part of every change instead of leaving them only in chat responses.

**Goals:**
- Add a standing rule to `AGENTS.md`.
- Store QA steps in discoverable Markdown files under `docs/qa/`.
- Give Milestone 2 a QA runbook matching the PR now open.

**Non-goals:**
- No application behavior changes.
- No new dependencies, automation, or CI jobs.
- No changes to the Milestone 2 design or plan.

**Constraints:**
- Follow the existing `AGENTS.md` structure.
- Use the repo's existing Markdown documentation conventions.
- Keep one file per change, named `YYYY-MM-DD-<topic>.md`.

**Approaches considered:**
1. Add the rule to `AGENTS.md`, create `docs/qa/2026-11-20-milestone-2-meal-logging.md`, and link it from PR #1. Recommended: discoverable and low-risk.
2. Append QA steps to the existing spec/plan. Rejected: mixes process with design history.
3. Only add the `AGENTS.md` rule. Rejected: does not provide a QA Markdown file for this change.

**Decision:** Approach 1.

**Design:**
- Add one bullet under `AGENTS.md` → `## Quality` requiring every change to include user-runnable QA steps in `docs/qa/YYYY-MM-DD-<topic>.md`, linked from the change summary or PR description.
- Create `docs/qa/2026-11-20-milestone-2-meal-logging.md` containing the automated gate, manual UI walkthrough, error-state check, mobile layout check, and snapshot-immutability check for PR #1.
- Update PR #1's description with a link to the QA runbook.
- Verify Markdown files are present and `make check` remains green.

**What is left to the implementer:** Exact wording of the AGENTS bullet and PR link sentence; the QA content is fixed by the approved approach and the prior Milestone 2 QA response.
