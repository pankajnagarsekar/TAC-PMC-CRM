# Superpowers: Making Your App Perfect 🦸

## What is Superpowers?

**Superpowers** is a comprehensive software development framework designed by Jesse Vincent (obra) that enhances AI coding agents with structured workflows and "skills" for building software better, faster, and with fewer bugs.

**GitHub**: https://github.com/obra/superpowers

---

## How Superpowers Works

Superpowers provides a **skill-based workflow system** that guides AI agents through structured development cycles:

### The Development Lifecycle

1. **Brainstorming** - Refine rough ideas through questions before coding
2. **Planning** - Create detailed implementation plans (red/green TDD focused)
3. **Implementing** - Execute tasks with subagent-driven development
4. **Testing** - Test-driven development (write tests first)
5. **Code Review** - Automated review against plan and quality standards
6. **Deployment** - Merge or PR workflows with verification

---

## Superpowers Skills Library

### Testing & Quality
- **test-driven-development** - RED-GREEN-REFACTOR cycle with best practices
- **systematic-debugging** - 4-phase root cause analysis
- **verification-before-completion** - Ensure fixes actually work

### Planning & Architecture
- **brainstorming** - Socratic design refinement
- **writing-plans** - Detailed implementation plans
- **software-architecture** - Structural design guidance

### Development
- **subagent-driven-development** - Parallel task execution with two-stage review
- **test-driven-development** - Enforce TDD principles
- **using-git-worktrees** - Isolated parallel development branches

### Code Review
- **requesting-code-review** - Pre-commit verification
- **receiving-code-review** - Respond to feedback systematically

### Deployment
- **finishing-a-development-branch** - Merge/PR decision workflow
- **dispatching-parallel-agents** - Concurrent subagent workflows

---

## Installation & Setup

### For Claude Code (Cowork Mode)
Superpowers is **built into Claude Code as plugins**. In a Claude Code context:

```bash
/plugin install superpowers@claude-plugins-official
```

Or via marketplace:
```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

### For Other Platforms
- **Cursor**: Search "superpowers" in plugin marketplace
- **Codex**: Follow https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.codex/INSTALL.md
- **OpenCode**: Follow https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.opencode/INSTALL.md
- **GitHub Copilot**: Use marketplace commands
- **Gemini CLI**: `gemini extensions install https://github.com/obra/superpowers`

---

## Applying Superpowers to Your TAC-PMC-CRM Mobile App

### Phase 1: Brainstorm & Design (With Superpowers)

When asked "help me make the mobile app perfect", Superpowers would:
1. Ask you clarifying questions about goals
2. Explore design alternatives
3. Present a refined spec in digestible chunks
4. Get your sign-off before proceeding

**Example conversation**:
```
You: "Make the mobile app perfect using superpowers"

Superpowers: "I'd like to understand your priorities first:
- Performance optimization (bundle size, load times)?
- Feature completeness (missing features)?
- Code quality (architecture, testing)?
- User experience (accessibility, design)?
- Reliability (error handling, offline support)?
- Security (credential handling, permissions)?

Which are most important?"
```

### Phase 2: Implementation Plan

Once priorities are set, Superpowers creates a detailed plan with:
- Clear file paths for changes
- Specific task breakdowns (2-5 minute tasks)
- Test-first approach for each task
- Verification steps

**Example plan**:
```
✓ Task 1: Add performance monitoring to DPR form
  - Write test for form performance
  - Implement performance metrics
  - Verify metrics collection

✓ Task 2: Improve error handling in auth flow
  - Write test for edge cases
  - Add error boundaries
  - Verify error recovery

✓ Task 3: Add accessibility features (WCAG 2.1 AA)
  - Write accessibility tests
  - Add ARIA labels
  - Test with screen readers
```

### Phase 3: Execution (Subagent-Driven)

Superpowers would:
- Dispatch fresh subagents for each task
- Review each task in two stages:
  1. **Spec compliance**: Does it match the plan?
  2. **Code quality**: Is it well-written, tested, maintainable?
- Flag blockers immediately
- Continue autonomously for hours if on-track

### Phase 4: Verification & Deployment

Before merge:
- ✅ All tests pass
- ✅ No linting errors
- ✅ Code review completed
- ✅ Performance benchmarks met
- ✅ Feature parity confirmed

---

## Superpowers + TAC-PMC-CRM Synergy

Your project already has **excellent foundations**:

### ✅ Already Aligned with Superpowers Philosophy
1. **DDD Architecture** - Clear bounded contexts (perfect for modular tasks)
2. **Monorepo Structure** - Easy parallel development with git worktrees
3. **Test-First Approach** - Pytest fixtures ready for TDD
4. **CI/CD Pipeline** - GitHub Actions for automated verification
5. **Skill-First Operating Manual** - See `AwesomeGSD_Skills.md`

### ✅ Ready for Superpowers Enhancement
- **RuFlo V3 Integration** - Already documented in CLAUDE.md
- **ReasoningBank Context** - Memory system for continuity
- **Subagent Support** - Swarm coordination ready
- **Zero-Error Policy** - Linting & testing enforced

---

## How to Make Your App Perfect (Practical Steps)

### Without Superpowers Plugin
You can implement Superpowers-inspired workflows manually:

#### 1. **Define "Perfect" (Brainstorm Phase)**
What does "perfect" mean for your app?
- ✅ Performance metrics (load time < 2s?)
- ✅ Feature completeness (all roles working?)
- ✅ Code quality (100% test coverage?)
- ✅ UX polish (accessibility, dark mode?)
- ✅ Reliability (error handling, offline support?)

#### 2. **Create Implementation Plan (Planning Phase)**
Break into small, testable tasks:
```markdown
## Mobile App Perfection Plan

### Performance (3 tasks)
- [ ] Optimize bundle size (remove dead code)
- [ ] Cache API responses (reduce network calls)
- [ ] Lazy-load heavy components

### Reliability (2 tasks)
- [ ] Add error boundaries
- [ ] Implement offline-first sync

### Accessibility (2 tasks)
- [ ] Add screen reader support
- [ ] Test with WCAG 2.1 AA
```

#### 3. **Execute with Testing (TDD Phase)**
For each task:
```bash
# 1. Write test (RED)
npm test -- --testNamePattern="task description"

# 2. Make test fail
npm test

# 3. Implement feature (GREEN)
# ... code changes ...

# 4. Run test again
npm test

# 5. Refactor if needed (REFACTOR)
# ... optimize code ...

# 6. Verify all tests pass
npm test
```

#### 4. **Review & Commit**
```bash
npm run lint
npm test
git add -A
git commit -m "feat: implement [task description]"
```

---

## Example: Make Camera Feature Perfect

### Brainstorm Phase
**Questions**:
- Current camera issues? (Performance? UX? Permissions?)
- Desired improvements? (Multiple photos? Video? OCR?)
- Constraints? (Bundle size? Permissions complexity?)

### Plan Phase
```markdown
1. Add photo quality options (100% test coverage)
   - Write test for quality selector
   - Add UI component
   - Implement image compression
   - Verify tests pass

2. Improve permission handling (error boundaries)
   - Write test for permission denial
   - Add user-friendly error messages
   - Implement retry logic

3. Add offline support
   - Write test for offline photo queueing
   - Implement queue logic
   - Add sync when online
```

### Execution Phase
```bash
# Task 1: Quality options
npm test -- --testNamePattern="photo quality"
# ... implement ...
npm test
npm run lint

# Task 2: Permissions
npm test -- --testNamePattern="permission handling"
# ... implement ...
npm test
npm run lint

# Task 3: Offline support
npm test -- --testNamePattern="offline photo"
# ... implement ...
npm test
npm run lint
```

---

## Superpowers Best Practices for Your App

### 1. **Skill-First Approach**
Before starting work, identify relevant skills:
- New feature? → @software-architecture + @react-best-practices + @testing
- Bug fix? → @debugging-toolkit + @testing + @error-detective
- UI change? → @design-system + @accessibility + @react-best-practices

### 2. **Test-Driven Development**
- Always write test first
- Watch it fail (RED)
- Write minimal code (GREEN)
- Refactor (REFACTOR)
- Commit atomic changes

### 3. **Planning & Verification**
- Break work into 2-5 minute tasks
- Each task has exact file paths
- Each task includes verification steps
- No task too large to review

### 4. **Code Review Checklist**
- [ ] Spec compliance (matches plan?)
- [ ] Test coverage (100% for new code?)
- [ ] No linting errors
- [ ] Performance benchmarks met
- [ ] Works on all platforms (iOS, Android, web)

---

## Resources

- **Superpowers Repository**: https://github.com/obra/superpowers
- **Blog Post**: https://blog.fsck.com/2025/10/09/superpowers/
- **Discord Community**: https://discord.gg/35wsABTejz
- **Your Project**: `CLAUDE.md` in root for integration

---

## Summary

**Superpowers makes your app perfect through**:
1. ✅ **Structured workflows** - Brainstorm → Plan → Execute → Review
2. ✅ **Test-driven development** - RED/GREEN/REFACTOR cycle
3. ✅ **Subagent coordination** - Parallel task execution
4. ✅ **Automated verification** - Tests, linting, code review
5. ✅ **Clear planning** - Breaking work into bite-sized pieces

**Your TAC-PMC-CRM mobile app is READY to benefit from Superpowers!** 🚀
