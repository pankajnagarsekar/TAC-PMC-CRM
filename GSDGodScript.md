1. Core Directives
Operating Mode: Interactive. You MUST stop for human approval at every Roadmap, Plan, and Verification gate.

Model Profile: Balanced. Use Opus for high-level planning and Sonnet for execution and verification.

Git Strategy: None (git.branching_strategy: none). All code changes are to be made on the current branch. Commits are automated for state tracking, but the human user manages merges and pushes.

Quality Standard: "World Class." Code must be modular, documented, and architecture-compliant.

2. Initialization & Context Refresh
Before accepting a task, the agent must ensure the planning environment is synchronized with the codebase.

Detection: Check for the existence of .planning/PROJECT.md.

Greenfield: If missing, run /gsd-new-project to establish the "dream extraction" and requirements.

Brownfield: If present, run /gsd-map-codebase to update the structure, architecture, and tech stack references in .planning/codebase/.

Sync: Run state sync via gsd-tools.cjs to ensure STATE.md reflects the actual filesystem.

3. Implementation Workflow
For every assigned task or module design, execute the following sequence:

Step A: Requirement & Design capture
Initiate /gsd-discuss-phase to identify "gray areas".

Optional Strict Skill: If the task involves UI, ask the user: "Would you like to generate a strict UI contract via /gsd-ui-phase?".

Step B: Strategic Planning
Run /gsd-plan-phase.

Optional Strict Skill: Ask the user: "Would you like to enable Nyquist Validation (Requirement-to-Test mapping) for this phase?".

The system must perform a Reachability Check to ensure all planned file edits are accessible.

Step C: Wave Execution
Execute via /gsd-execute-phase.

Each task requires an atomic commit following conventional formats (e.g., feat(module): description).

Schema Protection: If an ORM is detected, the agent must verify migrations are present to prevent schema drift.

4. Failure Recovery & Intelligence
If a task fails or a bug is reported for fixing:

Initial Repair: Attempt autonomous Node Repair (RETRY or DECOMPOSE) up to the configured budget (default 2).

Forensics: If repair fails, immediately run /gsd-forensics to analyze git history and artifact integrity for anomalies.

Halt: If forensics does not provide a definitive fix, the agent MUST Pause Work (/gsd-pause-work), generate a continue-here.md handoff, and wait for human intervention.

5. Delivery & Verification
Perform Post-Execution Verification against the original phase goals.

Conduct a Manual UAT walkthrough via /gsd-verify-work.

Security Option: Ask the user: "Would you like to perform a retroactive security audit via /gsd-secure-phase?".