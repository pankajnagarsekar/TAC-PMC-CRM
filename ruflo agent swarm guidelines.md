# RuFlo Agent Swarm: high-Precision Operational Guidelines

These guidelines are **NON-NEGOTIABLE**. They define the protocol for orchestrating specialized AI agent swarms while **bypassing interactive terminal delays**.

## 1. Tactical Environment Setup
Commands **MUST** be executed from the API root.
*   **WD**: `d:\_repos\TAC-PMC-CRM\apps\api`
*   **Prefix**: `npx -y ruflo@latest`

## 2. Zero-Delay Swarm Initialization
Do not wait for menu snapshots. Execute the command and immediately send the selection sequence.

### A. The "Specialized" Injection
```bash
# Command
npx -y ruflo@latest swarm start --objective "[NAME]" --strategy specialized

# Atomic Input Sequence (if prompted)
# [UP][UP][UP][UP][ENTER] -> Yes [ENTER]
```

## 3. High-Velocity Agent Spawning
Use Type IDs to bypass role descriptions.

### A. Spawn Reviewer/Architect (Type 1)
```bash
# Command
npx -y ruflo@latest agent spawn --type 1 --name "arch-reviewer"

# Atomic Input Sequence
# [ENTER] (Selects type) -> [ENTER] (Confirms name)
```

## 4. Logic Parity Audit (The "100% Completion" Check)
Completion is NOT file existence; it is functional parity. Before claiming "100%", the agent must:

1.  **Check Idempotency**: Verify `record_operation` and `check_idempotency` are in the new Service.
2.  **Check Transactions**: Verify `async with db_manager.transaction_session()` wraps all mutations.
3.  **Check Constants**: Verify `Decimal128` is used for ALL financial fields in the new Schema.
4.  **Audit Diff**: Run `grep` on root monolith files and ensure all business logic branches exist in `app/services/`.

## 5. Financial System Constitution
1.  **Architecture**: `Controller -> Service -> Repository`.
2.  **Precision**: Use `Decimal` and `Decimal128`.
3.  **Audit**: Mandatory `audit_service.log_action` on every state change.
4.  **Envelopes**: Every route MUST return `GenericResponse`.

## 6. Automation Sequence (Copypasta)
To create an architect and assign a review task in 10 seconds:
1. `npx -y ruflo@latest agent spawn --type 1 --name "reviewer-01"`
2. `npx -y ruflo@latest task create --objective "Logic Parity Audit" --agent reviewer-01`
   - Select **Refactor**
   - Prompt: "Compare [RootFile] with [DDDService]. Port missing idempotency, recalculation, and transaction logic."

---
**END GUIDELINES**
