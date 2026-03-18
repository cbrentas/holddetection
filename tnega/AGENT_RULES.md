# Agent Rules

You are working inside an existing repository with an established architecture.

Mandatory rules:

1. Build incrementally on the current codebase.
2. Do NOT refactor the overall architecture unless explicitly asked.
3. Do NOT rename or move existing files/directories unless explicitly asked.
4. Do NOT replace FastAPI, SQLAlchemy, Alembic, or the current worker pattern.
5. Do NOT change database schema unless the task explicitly requires a schema change.
6. Do NOT remove existing endpoints, services, or worker logic unless explicitly asked.
7. Prefer adding small focused files over rewriting large existing ones.
8. Keep the code modular, loosely coupled, and easy to extend.
9. Preserve the async job architecture: uploads -> jobs -> worker -> predictions/results.
10. Treat images as files/object storage references, never as DB blobs.
11. Keep storage backend abstraction-friendly so local storage can later be replaced by S3-compatible storage.
12. Do NOT add unnecessary frameworks or dependencies.
13. Do NOT add authentication systems beyond the current lightweight MVP auth unless explicitly asked.
14. Do NOT touch deployment or infrastructure files unless the task explicitly asks for it.
15. Do NOT commit secrets, credentials, weights, datasets, uploaded images, or generated results.
16. Work ONLY on the currently checked-out branch.
17. Do NOT switch branches, merge branches, rebase, or push to main.
18. Before making changes, inspect the current implementation and adapt to it rather than redesigning it.
19. Favor minimal, production-shaped changes over broad rewrites.
20. If a task is ambiguous, choose the smallest safe implementation that fits the current architecture.

Project priorities:
- scalability
- future-proof structure
- clean architecture
- compatibility with future web/app clients
- preservation of current architecture

Current architectural intent:
- FastAPI API layer
- SQLAlchemy + Alembic DB layer
- worker-based async inference
- model versioning in DB
- predictions stored in DB
- local filesystem storage for now, object storage later
- web first, app later

When done:
- summarize exactly what changed
- list files changed
- list follow-up recommendations separately from implemented work
- do not make extra architectural changes not requested