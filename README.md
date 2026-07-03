# Volta Memory

Persistent, typed, decaying memory for conversational agents — built for the Qwen Cloud Global AI Hackathon (Track 1: MemoryAgent).

Volta is a South African home-solar energy advisor persona demonstrating cross-session recall, timely forgetting, contradiction handling, and token-budgeted retrieval over a curated Postgres memory store.

## Architecture

- **Backend:** Python FastAPI — memory engine, Qwen Cloud integration, eval harness
- **Frontend:** Next.js — chat UI and memory transparency view
- **Database:** Postgres (local Docker or Alibaba RDS) with pgvector for hybrid retrieval
- **Deployment:** Alibaba Cloud ECS / Function Compute

See [ARCHITECTURE.md](./ARCHITECTURE.md) and [docs/00_Master_Index.md](./docs/00_Master_Index.md).

## Quick start

```bash
cp .env.example .env
# Fill in QWEN_API_KEY and DATABASE_URL

# Local Postgres (default)
docker compose --profile local-db up --build

# Or RDS-first: set DATABASE_URL to Alibaba RDS in .env, then:
docker compose up --build
```

Backend: http://localhost:8000  
Frontend: http://localhost:3000  
API docs: http://localhost:8000/docs

## Apply database schema

```bash
psql "$DATABASE_URL" -f backend/migrations/001_initial.sql
```

## Run tests

```bash
cd backend && pip install -e ".[dev]" && pytest
```

## Eval harness

```bash
cd backend && python -m eval.run_eval
```

Results are written to [BENCHMARKS.md](./BENCHMARKS.md).

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/03_Memory_System_Design.md](./docs/03_Memory_System_Design.md) | Core memory design |
| [docs/04_Database_Schema.md](./docs/04_Database_Schema.md) | SQL schema |
| [docs/05_API_Reference.md](./docs/05_API_Reference.md) | HTTP API |
| [docs/09_Environment_Variables.md](./docs/09_Environment_Variables.md) | Full env reference |

## License

MIT — see [LICENSE](./LICENSE).
