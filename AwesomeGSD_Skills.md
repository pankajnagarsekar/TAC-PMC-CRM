# Project Operating Manual — Skill-First Workflow

**Last Updated:** 2026-05-03
**Project:** TAC-PMC-CRM
**Tech Stack:** React 19 (Frontend) | FastAPI/Fastify (Backend) | Next.js 16 | MongoDB | Tailwind 4
**Design Language:** Luxury Industrial

---

## 1. The Skill-First Rule ⚙️

**MANDATORY:** For **EVERY** task (analysis, bug fixing, feature creation, UI adjustment, database changes, or refactoring), you MUST:

1. **Identify the most relevant skills** by searching the `.agents/skills` (project-specific) or `C:\Users\panka\.gemini\antigravity\skills` (latest system-wide skills) directories.
2. **Document which skills are being used** in your response before beginning work
3. **Stack skills strategically** (see section 2 below) for complex tasks
4. **Verify alignment** with project specifications before writing any code
5. **Code Simplification**: Use the `@code-simplifier` skill to write all new code.
6. **React Quality Check**: After any React code is written, run `@react-doctor` to scan the code, and ensure all identified issues are fixed immediately.
7. **Mandatory Post-Fix Validation**: For every code modification, you MUST run `@lint-and-validate` and `@verification-before-completion` to ensure zero regressions or orphaned variables.

### Why This Matters
- Ensures consistency across all changes
- Prevents architectural drift
- Makes decisions auditable and repeatable
- Reduces rework and miscommunication

---

## 2. Mandatory Skill Stacking 🔧

Stack skills based on task type. Always include the base skill(s) plus context-specific skills:

Primary: @error-detective + @debugging-toolkit + @software-architecture + @systematic-debugging + @lint-and-validate
Secondary: @error-diagnostics-smart-debug + @bug-hunter + @vibe-code-auditor + @error-debugging-multi-agent-review + @verification-before-completion + @code-reviewer
Example: When fixing a database query failure, use @systematic-debugging to isolate the root cause, followed by @lint-and-validate to ensure no syntax/import regressions.

### New Feature Implementation
```
Primary: @software-architecture + @concise-planning + @[language]-pro + @ai-ml + @code-simplifier
Secondary: @writing-plans + @executing-plans + @pydantic-ai + @langgraph + @ai-engineer
Example: Adding a new CRM field requires @react-best-practices (frontend) + @python-pro (backend) + @database-design (schema)
```

### Complex Orchestration & Governance
```
Primary: @agent-manager-skill + @concise-planning + @writing-plans
Secondary: @antigravity-skill-orchestrator + @verification-before-completion + @requesting-code-review
Usage: EVERY major task must be initialized with a clear PLAN.md using @writing-plans.
```

### UI/UX Adjustments & Components
```
Primary: @antigravity-design-expert + @tailwind-design-system + @react-best-practices + @shadcn + @code-simplifier + @react-doctor
Secondary: @accessibility-compliance + @performance-optimizer + @magic-ui-generator + @threejs-skills + @scroll-experience + @design-spells + @spline-3d-integration
Example: Any design change must maintain the Luxury Industrial aesthetic using @antigravity-design-expert principles
```

### Database Schema & Data Changes
```
Primary: @database-design + @data-integrity-patterns + @prisma-expert + @drizzle-orm-expert
Secondary: @neon-postgres + @supabase-automation + @sql-pro + @database-admin
Example: Schema modifications must preserve financial integrity and include migration tests
```

### API Development & Integration
```
Primary: @api-design-principles + @[language]-pro + @security-best-practices + @api-patterns
Secondary: @trpc-fullstack + @hono + @error-handling-patterns + @api-endpoint-builder + @zod-validation-expert
```

### Research, Intelligence & Automation
```
Primary: @exa-search + @tavily-web + @agentfolio + @deep-research + @skyvern-browser-automation
Secondary: @agentmail + @hubspot-automation + @slack-automation + @shopify-development + @whatsapp-automation + @not-human-search-mcp
Example: Use @skyvern-browser-automation for complex web-based workflows or @exa-search for deep competitor analysis.
```

### Media, Video & AI Generation
```
Primary: @fal-generate + @videodb-skills + @remotion + @audio-transcriber + @seek-and-analyze-video
Secondary: @magic-animator + @youtube-summarizer + @imagen + @stable-ai
Example: Analyze complex video data with @seek-and-analyze-video or generate premium walkthroughs using @remotion.
```

---

## 3. Strict Context Alignment 📋

All code modifications **MUST** align with the following specifications. These are not optional:

### Frontend (React, UI/UX, Components)
**Authority:** `Enterprise Frontend Engineering Specification.md`
- Component structure and naming conventions
- State management patterns (Context API, Redux patterns)
- Styling system (Tailwind CSS with Luxury Industrial design tokens)
- Accessibility requirements (WCAG 2.1 AA compliance)
- Performance targets (Core Web Vitals)
- Testing standards (unit tests, integration tests, e2e tests)

**Mandatory Checks Before Any UI Code:**
- [ ] Does this component follow the established naming convention?
- [ ] Are all new UI elements styled according to the Luxury Industrial design language?
- [ ] Have accessibility attributes been added (aria-*, alt-text, semantic HTML)?
- [ ] Is the component performance-tested?
- [ ] Does it work on both web and mobile viewports?

### Backend, Database & Financial Integrity
**Authority:** `Backend Database Schema & Financial Integrity Specification.md`
- Database schema and relationships
- Data validation rules
- Financial calculation methods (cash flow, budgeting, forecasting)
- Audit trail requirements
- Transaction integrity constraints
- API response format and error handling
- Security and authentication patterns

**Mandatory Checks Before Any Data/Backend Code:**
- [ ] Does this change preserve referential integrity?
- [ ] Are financial calculations verified against the specification?
- [ ] Is an audit trail entry created for changes?
- [ ] Are all inputs validated?
- [ ] Does the change require database migration? (If yes, include migration file)
- [ ] Have edge cases been tested (negative values, zero, null, overflow)?

---

## 4. Verification Protocol ✅

**MANDATORY:** After any code modification, output a **Verification Step** using `@testing-patterns`:

### GStack Pre-Review Audit Gates:
Prior to completing validation safeguards, execute the corresponding GStack audits:
- `/review` to audit branch logic and auto-fix simple bugs.
- `/cso` to perform OWASP Top 10 + STRIDE threat modeling.
- `/design-review` (for frontend modifications) to check against Luxury Industrial styles.

### Format:
```markdown
## Verification Step

**Skill Used:** @testing-patterns

**Tests Created/Run:**
- [ ] Unit test: [test name]
- [ ] Integration test: [test name]
- [ ] E2E test (if applicable): [test name]

- [ ] **Zero Error State**: Full `pnpm lint` and `pytest` are Green (via @lint-and-validate)
- [ ] **Orphaned Variable Check**: No references to deleted state/props (via @verification-before-completion)
- [ ] **React Quality Check**: `@react-doctor` has scanned the React code and all issues are fixed
- [ ] **Logic Integrity**: All modified functions pass logical audit (via @code-reviewer)
- [ ] **Path Integrity**: No hardcoded Windows backslashes `\` or `.exe` in configs
- [ ] **Discovery Isolation**: `pytest.ini` correctly points to the `tests/` folder
- [ ] Performance baseline met
- [ ] No console warnings or errors
- [ ] Accessibility checks passed (if UI change)
- [ ] Specification alignment verified
```

---

## 5. Project Tech Stack & Architecture 🏗️

### Frontend
- **Framework:** React 18+ / Next.js 14+
- **Styling:** Tailwind CSS (Luxury Industrial aesthetic)
- **State Management:** React Context API / Zustand / TanStack Query
- **Testing:** Jest, React Testing Library, Playwright

### Backend
- **Runtime:** Node.js (Express/Fastify) / Hono
- **API Server:** Python (FastAPI) for heavy computation / ML
- **Agent Framework:** PydanticAI / LangGraph
- **Testing:** Jest, pytest, Vitest

---

## 6. Code Modification Workflow 📝

All work follows a systematic skill-driven lifecycle to ensure quality and specification alignment.

### Phase 1: Analysis & Scoping
- **Context Mapping**: Use `@analyze-project` or `@software-architecture` to map relevant files and dependencies.
- **Requirement Validation**: Verify the task against `Enterprise Frontend Engineering Specification.md` or `Backend Database Schema & Financial Integrity Specification.md`.

### Phase 2: Planning
- **Skill Selection**: Identify the stack of `@skills` needed for the task.
- **Technical Plan**: Use `@concise-planning` or `@writing-plans` to generate a detailed implementation strategy.
- **Approval**: Present the plan to the user for validation before modifying code.

### Phase 3: Implementation
- **Execution**: Use `@executing-plans` for disciplined execution of the approved plan.
- **Code Simplification**: Use `@code-simplifier` to write and optimize all new code.
- **Pattern Adherence**: Use language-specific skills (e.g., `@javascript-pro`, `@python-pro`) to ensure idiomatic code.
- **React Quality Check**: Run `@react-doctor` after writing React code and ensure all identified issues are fixed.
- **Incremental Commits**: Commit logical units of work following the project's commit standards.

### Phase 4: Verification & Shipping
- **Validation**: Run the mandatory `@testing-patterns` checklist.
- **Final Review**: Use `@verification-before-completion` to ensure all edge cases are handled.
- **PR Readiness**: Use `@requesting-code-review` to summarize changes and prepare for merge.

---

## 7. Emergency / Technical Debt Protocol 🚨

**When you encounter a deviation from specifications:**

1. **Document it:** Add to the issue/PR description with `[SPEC-DEVIATION]` tag
2. **Root cause:** Determine if it's a spec gap or intentional bypass
3. **Decision:**
   - If gap: Update specification immediately
   - If intentional: Require explicit user approval + document in commit
4. **Track:** Add to technical debt backlog for future refactoring

---

## 8. Git Workflow & Commits 💻

### Commit Message Format
```
[type]: Brief description

Detailed explanation of changes and reasoning.

Skills Used: @skill1, @skill2
Specification(s) Aligned: [specification name]
Tests Added/Modified: [test names]
```

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

### PR Requirements
- Reference relevant issue(s)
- Include Verification Step checklist
- Link to specification sections affected
- Require approval before merge if:
  - Database schema changes
  - Financial logic changes
  - API contract changes

---

## 9. Design System: Luxury Industrial 🎨

The project uses a "Luxury Industrial" aesthetic:

- **Color Palette:** Deep metallics, muted golds, charcoal grays, soft whites
- **Typography:** Modern geometric sans-serif for headers, readable serif for body text
- **Spacing:** Balanced whitespace, grid-based 4px/8px/16px increments
- **Components:** Minimalist, high-contrast, sophisticated simplicity
- **Interactions:** Smooth animations, meaningful micro-interactions

**Mandatory:** All new UI components must be reviewed against design tokens in the specification.

---

## 10. Contact & Escalation 📞

- **Specification Updates:** Create an issue with `[SPEC-UPDATE]` tag
- **Architecture Questions:** Use `@software-architecture` skill
- **Design Questions:** Use `@antigravity-design-expert` skill
- **Data Integrity Questions:** Use `@database-admin` skill
- **Autonomous Operations:** Use `@agent-orchestrator` or `@antigravity-skill-orchestrator`

---

## 11. Latest Skills & Standards 🛠️

For the most up-to-date agent capabilities, always refer to the system-wide skills directory:
`C:\Users\panka\.gemini\antigravity\skills`

These skills should be used in conjunction with project-specific skills in `.agents/skills` to ensure the highest quality of implementation.

---

## 12. Emerging Multi-Agent & Research Patterns 🧠

Leverage these advanced patterns for high-complexity tasks:

- **Autonomous Engineering**: Use `/autoplan` and `/ship` from the **GStack** framework for end-to-end task orchestration. Refer to [GStack.md](file:///d:/_repos/TAC-PMC-CRM/GStack.md) for full protocol details.
- **Parallel Research**: Use `@infinite-gratitude` for large-scale data gathering across 10+ agents.
- **Task Dispatching**: Use `@dispatching-parallel-agents` when handling 2+ independent sub-tasks.
- **Persistent Knowledge**: Use `@agent-memory-mcp` to maintain architectural context across sessions.
- **Workflow Loops**: Use `@stitch-loop` for autonomous iterative UI building.

---

## 13. Premium Media & Design Spells ✨

To achieve the **"Luxury Industrial" WOW factor**, integrate these "spells":

- **Micro-interactions**: `@design-spells` for that final 1% of polish.
- **3D Experiences**: `@spline-3d-integration` and `@threejs-skills` for immersive dashboards.
- **Dynamic Content**: `@fal-generate` and `@videodb-skills` for high-fidelity assets.
- **Rapid Prototyping**: `@magic-ui-generator` to compare production-ready components instantly.

---

**Document Owners:** TAC-PMC-CRM Development Team
**Review Frequency:** Monthly
**Last Review:** 2026-05-03
