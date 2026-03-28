# CLAUDE.md — Project Operating Manual

**Last Updated:** 2026-03-21
**Project:** TAC-PMC-CRM
**Tech Stack:** React.js (Frontend) | Node.js (Backend) | Python (API Server) | MongoDB (Database)
**Design Language:** Luxury Industrial

---

## 1. The Skill-First Rule ⚙️

**MANDATORY:** For **EVERY** task (analysis, bug fixing, feature creation, UI adjustment, database changes, or refactoring), you MUST:

1. **Identify the most relevant skills** by searching the `.claude/skills` directory for applicable skill files
2. **Document which skills are being used** in your response before beginning work
3. **Stack skills strategically** (see section 2 below) for complex tasks
4. **Verify alignment** with project specifications before writing any code

### Why This Matters
- Ensures consistency across all changes
- Prevents architectural drift
- Makes decisions auditable and repeatable
- Reduces rework and miscommunication

---

## 2. Mandatory Skill Stacking 🔧

Stack skills based on task type. Always include the base skill(s) plus context-specific skills:

### Error Detection & Debugging
```
Primary: @error-detective + @debugging-toolkit + @software-architecture
Example: When fixing a database query failure, also check data integrity patterns
```

### New Feature Implementation
```
Primary: @software-architecture + @concise-planning + @[language]-pro
Example: Adding a new CRM field requires @react-best-practices (frontend) + @python-pro (backend) + @database-design (schema)
```

### Complex Orchestration & Governance
```
Primary: @gsd-manager + @gsd-new-project + @gsd-plan-phase
Secondary: @antigravity-skill-orchestrator + @concise-planning
Usage: EVERY major task must be initialized as a GSD milestone or phase.
```

### UI/UX Adjustments & Components
```
Primary: @antigravity-design-expert + @tailwind-design-system + @react-best-practices
Secondary: @accessibility-compliance + @performance-optimizer
Example: Any design change must maintain the Luxury Industrial aesthetic using @antigravity-design-expert principles
```

### Database Schema & Data Changes
```
Primary: @database-design + @data-integrity-patterns + @sql-pro
Secondary: @backend-architect + @testing-patterns
Example: Schema modifications must preserve financial integrity and include migration tests
```

### API Development & Integration
```
Primary: @api-design-principles + @[language]-pro + @security-best-practices
Secondary: @testing-patterns + @error-handling-patterns
```

### Performance Optimization
```
Primary: @performance-profiling + @performance-optimizer + @[language]-patterns
Secondary: @monitoring + @observability-engineer
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

### Format:
```markdown
## Verification Step

**Skill Used:** @testing-patterns

**Tests Created/Run:**
- [ ] Unit test: [test name]
- [ ] Integration test: [test name]
- [ ] E2E test (if applicable): [test name]

**Verification Checklist:**
- [ ] Code runs without errors
- [ ] All new functions have test coverage
- [ ] Edge cases tested (null, undefined, empty, boundary values)
- [ ] Performance baseline met
- [ ] No console warnings or errors
- [ ] Accessibility checks passed (if UI change)
- [ ] Specification alignment verified
```

### When to Skip Verification
Only skip if:
- The change is documentation-only (comments, CLAUDE.md updates)
- The change is configuration-only (env vars, non-code files)
- Explicitly instructed by the user

---

## 5. Project Tech Stack & Architecture 🏗️

### Frontend
- **Framework:** React 18+
- **Styling:** Tailwind CSS
- **Design System:** Luxury Industrial aesthetic
- **State Management:** React Context API / Redux (as needed)
- **Testing:** Jest, React Testing Library, Playwright
- **Build Tool:** Turbo (monorepo), Vite/Next.js

### Backend
- **Runtime:** Node.js (Express/Fastify patterns)
- **API Server:** Python (FastAPI) for heavy computation
- **Language:** TypeScript (frontend), JavaScript (backend), Python (API/ML)
- **Testing:** Jest, pytest, Vitest

### Database
- **Primary:** MongoDB
- **ORM/ODM:** Mongoose / Prisma
- **Querying:** Aggregation pipelines for complex financial queries
- **Backups:** Regular automated backups required

### Financial Logic
- All monetary calculations use **fixed-point arithmetic** (no floating-point)
- All transactions logged to audit trail
- No direct database mutations—always use validated business logic layers
- Reconciliation and variance tracking required

---

## 6. Code Modification Workflow 📝

Management of all work follows the **GSD (Get Shit Done)** protocol combined with specific technical skills.

### Phase 1: GSD Initialization
- **Brownfield/Start**: Use `/gsd-map-codebase` to refresh the agent's map.
- **New Task**: Use `/gsd-plan-phase "[Task Title]"` to create a structured implementation plan in `.planning/`.
- **Review**: The user must approve the `PLAN.md` before execution.

### Phase 2: Skill Identification & Stacking
- Once the GSD phase is active:
- "I will use @[skill1] + @[skill2] + @[skill3] for the implementation of this phase because..."
- Note: Use @antigravity-skill-orchestrator for complex, multi-domain tasks within the phase.

### Phase 3: Specification Review
- Read relevant specifications (Frontend/Backend) as defined in the GSD plan.
- Identify constraints and mandatory patterns.

### Phase 4: Implementation
- Execute the task using `/gsd-execute-phase` or manual step-by-step logic.
- Include inline documentation for complex logic.
- Commit incrementally following the GSD commit tool standards.

### Phase 5: Verification & Completion
- Run verification tests as specified in Section 4.
- Output the mandatory Verification Step checklist.
- Mark phase as complete via `/gsd-verify-work`.

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
- **Architecture Questions:** Use `@software-architect` skill
- **Design Questions:** Use `@antigravity-design-expert` skill
- **Data Integrity Questions:** Use `@database-architect` skill

---

## Summary: The Three Mandatory Rules

1. **Skill-First:** Always identify and stack relevant skills before starting work
2. **Specification-Aligned:** All code must conform to the Frontend or Backend specification
3. **Verification-Required:** Output a Verification Step after every code modification

**These rules are non-negotiable.** Deviation requires explicit user approval and documentation.

---

**Document Owners:** TAC-PMC-CRM Development Team
**Review Frequency:** Quarterly or as needed
**Last Review:** 2026-03-21
