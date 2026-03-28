# Project: TAC-PMC-CRM DDD Restructuring

## Context
The project is a full-stack CRM with a luxury industrial aesthetic. It is currently in a transitional state between a monolithic folder structure and a modular Domain-Driven Design (DDD) architecture. The objective is to complete this migration across the entire backend API.

## Objectives
- Implement strict DDD structure with defined Bounded Contexts.
- Isolate domain logic into aggregate roots, entities, and value objects.
- Maintain full backward compatibility for all existing API endpoints.
- Decouple cross-cutting concerns into a Shared Kernel.

## Tech Stack
- Python 3.12+ (FastAPI)
- MongoDB (Motor)
- Domain-Driven Design (DDD)
- RuFlo Swarm Orchestration
