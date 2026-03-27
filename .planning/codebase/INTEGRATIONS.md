# External Integrations

## Core Infrastructure
- **Database (MongoDB)**: Primary data store, accessed via `MONGO_URL` and `DB_NAME` in config.
- **Cache & Message Broker (Redis)**: Used for shared state, rate limiting, and Celery task brokerage.
- **Object Storage (S3)**: Integrated via `boto3` for file uploads (Site documents, DPR attachments).

## Third-Party APIs
- **OpenAI**: Integrated for AI-powered summaries and intelligence features.
- **AWS**: Used for various cloud services beyond just storage.

## Authentication & Authorization
- **JWT**: Stateless session management using `HS256`.
- **RBAC**: Custom permission checker system injected into routes.

## Notifications
- Integrated notification system (found in `notification_routes.py`) for system alerts.
