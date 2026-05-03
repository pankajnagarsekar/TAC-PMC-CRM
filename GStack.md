# GStack Framework Integration — TAC-PMC-CRM

This document serves as the authoritative guide for using the **GStack** framework within the TAC-PMC-CRM project. GStack is a suite of 23+ opinionated specialist agents designed to accelerate development, improve code quality, and automate testing.

---

## 🚀 Quick Start
To leverage GStack, use the following slash commands in your chat session:
- `/office-hours` — Start here for any new feature or architecture discussion.
- `/autoplan` — Automatically generate a fully reviewed implementation plan.
- `/review` — Perform a staff-engineer level code review on your current branch.
- `/qa` — Run automated browser-based tests against a staging URL.
- `/ship` — Automate the final checks, testing, and PR creation.

---

## 🛠️ Usage by Workflow

### 1. Error Fixing & Debugging
When facing bugs or regressions, follow the **"Investigate First"** protocol:
- **`/investigate`**: Systematic root-cause debugging. It traces data flow, tests hypotheses, and prevents "trial-and-error" fixes.
- **`/guard`**: Activates `/careful` (safety warnings) and `/freeze` (locks edits to specific directories) to prevent collateral damage during debugging.
- **`/review`**: Run after a fix to ensure no new regressions were introduced and that the code meets production standards.
- **`/qa`**: Re-verify the fix in a real browser environment to ensure the user flow is restored.

### 2. New Feature Development
Use the **"Think → Plan → Build"** cycle:
- **`/office-hours`**: Interrogate the product idea. It asks forcing questions to reframe the problem and ensure you're building the right thing.
- **`/plan-ceo-review`**: Strategic challenge of the scope. Ensures the feature has a "10-star" experience.
- **`/plan-eng-review`**: Locks in the architecture, data flow, and test matrix before a single line of code is written.
- **`/autoplan`**: A shortcut that runs the CEO, Design, and Eng reviews sequentially to produce a shippable plan.
- **`/codex`**: Get a second opinion from an independent AI model on the architectural choices.

### 3. Updating Existing Development
For refactoring, minor updates, or extending features:
- **`/plan-devex-review`**: Audit the developer experience. Essential if you're updating APIs, SDKs, or internal tools.
- **`/design-review`**: Audit the UI/UX against the "Luxury Industrial" standards. It identifies "AI slop" and visual inconsistencies.
- **`/design-shotgun`**: Explore visual options for UI updates by generating multiple mockup variants.
- **`/document-release`**: Automatically update `README.md`, `CLAUDE.md`, and other docs to reflect the changes.

### 4. Testing & Quality Assurance
GStack treats testing as a first-class citizen:
- **`/qa`**: The agent opens a real Chromium browser, performs clicks/navigation, and finds bugs. It then attempts to fix them and re-verify.
- **`/qa-only`**: Identical to `/qa` but generates a bug report instead of applying code fixes.
- **`/benchmark`**: Baseline page load times and Core Web Vitals. Use this to ensure updates don't degrade performance.
- **`/cso`**: Chief Security Officer audit. Scans for OWASP Top 10 vulnerabilities and STRIDE threats with zero-noise filtering.

### 5. Governance, Safety & Documentation
- **`/careful`**: Prevents destructive commands (like `rm -rf` or `force-push`) without explicit confirmation.
- **`/freeze` / `/unfreeze`**: Locks/unlocks specific directories to prevent accidental edits in sensitive areas.
- **`/retro`**: Run at the end of a sprint or major task to reflect on what was learned and identify growth opportunities.
- **`/gstack-upgrade`**: Keeps the GStack library updated with the latest agentic patterns.

---

## 📋 GStack Command Reference

| Command | Specialist Role | Primary Function |
|:---|:---|:---|
| `/office-hours` | YC Office Hours | Product interrogation & design doc generation |
| `/autoplan` | Review Pipeline | CEO → Design → Eng review automation |
| `/plan-ceo-review`| CEO / Founder | Strategic scope challenge & 10-star product focus |
| `/plan-eng-review`| Eng Manager | Architecture, data flow, and test matrix locking |
| `/review` | Staff Engineer | Deep code audit, bug finding, and auto-fixing |
| `/qa` | QA Lead | Real browser testing, bug fixing, and verification |
| `/ship` | Release Engineer | Final tests, coverage audit, and PR opening |
| `/investigate` | Debugger | Systematic root-cause investigation |
| `/cso` | Security Officer | OWASP Top 10 + STRIDE threat modeling |
| `/browse` | QA Engineer | Real-time browser interaction (screenshots/clicks) |
| `/retro` | Eng Manager | Performance reflection and pattern learning |

---

## ⚡ Integrated Workflow Example
1. **Discuss**: `/office-hours` "I want to add a real-time notification system."
2. **Plan**: `/autoplan`
3. **Approve**: "Approve plan. Exit plan mode."
4. **Code**: [Implement features]
5. **Audit**: `/cso` (Security check)
6. **Review**: `/review`
7. **Test**: `/qa https://staging.tac-pmc.com`
8. **Ship**: `/ship`
9. **Reflect**: `/retro`

---
> [!IMPORTANT]
> Always use `/browse` from GStack for web tasks. It provides 100ms response times and real Chromium rendering, outperforming standard MCP tools.
