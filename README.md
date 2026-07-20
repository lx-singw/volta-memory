# Volta Memory

**A Qwen-powered MemoryAgent for home-energy decisions that can show what it knows, what changed, and why its advice is still current.**

Volta does not treat a conversation transcript as memory. It stores typed, source-linked observations; detects corrections; preserves superseded facts for accountability; applies selective forgetting; and exposes the evidence used in each recommendation.

## Live proof

- Current Function Compute deployment: [app](https://volta-m-backend-mlutvrvuqy.ap-southeast-1.fcapp.run) | [memory view](https://volta-m-backend-mlutvrvuqy.ap-southeast-1.fcapp.run/memory) | [health](https://volta-m-backend-mlutvrvuqy.ap-southeast-1.fcapp.run/health)
- Judge showcase: `/showcase` is the immutable correction story.
- Private trial: `/try` creates an isolated workspace rather than changing the showcase.

The production cutover target is **OSS/CDN -> API Gateway -> Function Compute 3.0 -> RDS PostgreSQL + pgvector**. The current FC URL above remains a verification endpoint until the CDN and gateway domains in `VOLTA_PUBLIC_APP_ORIGIN` and `VOLTA_PUBLIC_API_BASE_URL` are configured.

## Why this is a MemoryAgent

1. **Persistent memory:** information survives session boundaries in PostgreSQL.
2. **Corrections with accountability:** R3,200 can become R3,800 without deleting the original evidence.
3. **Selective forgetting:** decayed or irrelevant memories remain auditable but are excluded from advice.
4. **Limited-context recall:** retrieval ranks current, high-value facts into a fixed token budget.
5. **Explainability:** the answer can show what was used, what was considered, and what was deliberately not used.

## Judge path

Use the 3-minute sequence in [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md):

1. Confirm a bill of R3,200 and the preference to keep lights on.
2. Correct the bill to R3,800.
3. End the session and inspect the lifecycle receipt.
4. Open the Memory Map and follow the current-to-superseded relation.
5. Ask for advice in a new session and inspect “Why this advice.”

## Measured evidence

The checked-in artifact records one completed 132-case, three-replicate comparative sweep with Qwen `qwen-max`; all 132 cases completed successfully for evaluator commit `cf845c7e`. That report shows that Volta persisted all six tested supersession chains in the database, improved selective-forgetting accuracy over the memory-capable baselines, and trades some full-history recall for governed retrieval. It does **not** claim perfect downstream correction or perfect exclusion. Any later lifecycle/retrieval code change requires a fresh full sweep and regenerated artifacts before its metrics are presented as release evidence.

- [Benchmark report](BENCHMARKS.md)
- [Machine-readable summary](backend/eval/artifacts/evaluation-summary.json)
- [Sanitized per-case measurements](backend/eval/artifacts/evaluation-cases.jsonl)
- [Evaluation method and limitations](EVALUATION.md)

## Architecture and cloud proof

- [Architecture](ARCHITECTURE.md)
- [Architecture diagram](docs/architecture.svg)
- [Production operations](deployment/alibaba/production-operations.md)
- [Deployment verification script](deployment/proof/deployment_verification.py)
- [Security model](SECURITY.md)

## Local development

```bash
# Backend
cd backend
python3 -m pip install -e .
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend, in another terminal
cd frontend
npm install
npm run dev
```

Localhost is permitted only during development. Static production releases are blocked if they contain a localhost API reference.

## Production release contract

Before a static release, configure only non-secret public origins in the release environment:

```bash
export APP_ENV=production
export VOLTA_PUBLIC_APP_ORIGIN=https://app.example.com
export VOLTA_PUBLIC_API_BASE_URL=https://api.example.com
python scripts/build_static_release.py
python scripts/upload_frontend.py
```

`build_static_release.py` writes `runtime-config.js` before the Next build and validates the exported output. It never places a Qwen key, database URL, or cloud credential in the static bundle. See [production operations](deployment/alibaba/production-operations.md) for gateway, RAM, Secrets Manager, SLS, migration, and smoke-test requirements.

## Submission assets

- [Submission checklist and copy](SUBMISSION.md)
- [Generated judge deck](docs/volta_memory_deck.pptx)
- [Demo runbook](DEMO_RUNBOOK.md)

The public video URL must be added to `SUBMISSION.md` after it is uploaded and verified as publicly viewable.
