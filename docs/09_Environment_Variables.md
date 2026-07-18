# Volta Memory — Complete Environment Variable Reference
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**
**Every variable required to run, deploy, benchmark, and publish the full project**

---

## Table of Contents
- [1. How to Use This Document](#1-how-to-use-this-document)
- [2. Qwen Cloud — Inference](#2-qwen-cloud--inference)
- [3. Alternative LLM Backends — Provider-Agnostic Proof](#3-alternative-llm-backends--provider-agnostic-proof)
- [4. Database](#4-database)
- [5. Alibaba Cloud — Deployment](#5-alibaba-cloud--deployment)
- [6. Memory Engine Tuning](#6-memory-engine-tuning)
- [7. Hybrid Retrieval & Embeddings](#7-hybrid-retrieval--embeddings)
- [8. Adversarial Defence & Plausibility](#8-adversarial-defence--plausibility)
- [9. Consolidation Cycle](#9-consolidation-cycle)
- [10. Eval Harness](#10-eval-harness)
- [11. Explainability](#11-explainability)
- [12. Application & Server](#12-application--server)
- [13. Hosted Live Demo](#13-hosted-live-demo)
- [14. Frontend](#14-frontend)
- [15. Package Publishing (Standalone Library)](#15-package-publishing-standalone-library)
- [16. Observability & Logging](#16-observability--logging)
- [17. Full .env.example File](#17-full-envexample-file)
- [18. Secrets Handling & Security Notes](#18-secrets-handling--security-notes)
- [19. Per-Environment Variable Matrix](#19-per-environment-variable-matrix)

---

## 1. How to Use This Document

Every variable below states: what it does, whether it's required or optional, its default (if any), which file/module reads it, and any security note. `backend/app/config.py` is the single source of truth that loads and validates all of these at startup — the application should fail fast with a clear error if a required variable is missing, not fail silently mid-request.

---

## 2. Qwen Cloud — Inference

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `QWEN_API_KEY` | Yes | — | `chat/qwen_client.py` | Auth key for Qwen Cloud API. Every inference call in the critical path routes through this. |
| `QWEN_API_BASE_URL` | Yes | `https://dashscope.aliyuncs.com/api/v1` | `chat/qwen_client.py` | Base endpoint — kept configurable rather than hardcoded so regional endpoints or future API version changes don't require a code change. |
| `QWEN_MODEL_CHAT` | Yes | `qwen-max` | `chat/qwen_client.py`, `volta_prompt.py` | Model used for conversational responses. `qwen-max` for quality; `qwen-plus` as a cheaper alternative worth benchmarking against in the eval harness's cost metrics. |
| `QWEN_MODEL_EXTRACTION` | Yes | `qwen-plus` | `memory/extraction.py` | Model used for end-of-session memory extraction. Deliberately allowed to differ from the chat model — extraction is a structured, lower-creativity task that may not need the largest model, which is itself a cost-efficiency data point worth reporting in BENCHMARKS.md. |
| `QWEN_MODEL_EMBEDDING` | Yes (if hybrid retrieval enabled) | `text-embedding-v2` | `memory/embeddings.py` | Qwen's embedding endpoint for the hybrid retrieval fallback (Memory Design Doc §13). |
| `QWEN_MAX_RETRIES` | No | `3` | `chat/qwen_client.py` | Retry count on transient API failures before surfacing an error. |
| `QWEN_TIMEOUT_SECONDS` | No | `30` | `chat/qwen_client.py` | Hard timeout per API call — prevents a hung request from stalling a demo session indefinitely. |

**Security note:** `QWEN_API_KEY` must never appear in logs, error messages, or the `explainability.py` trace output. `config.py` should redact it in any startup log line that prints loaded configuration.

---

## 3. Alternative LLM Backends — Provider-Agnostic Proof

These back the third reference example (Productization Doc §2, §8) proving the `LLMBackend` protocol genuinely decouples from Qwen.

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `OPENAI_API_KEY` | Only for `examples/openai_customer_support/` | — | `volta_memory/llm_backend.py` (OpenAIBackend implementation) | Proves the standalone package works against a second provider. Not required for the core Volta/Qwen demo. |
| `OPENAI_MODEL_CHAT` | No (if above set) | `gpt-4o-mini` | Same | Model for the third example's chat completion. |
| `LLM_BACKEND_DEFAULT` | No | `qwen` | `volta_memory/__init__.py` | Selects which backend implementation the package instantiates by default when not explicitly specified by the caller. |

---

## 4. Database

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `DATABASE_URL` | Yes | — | `app/db.py` | Full Postgres connection string. Points to local Postgres in dev, Alibaba RDS in production. Format: `postgresql://user:password@host:port/dbname` |
| `DATABASE_POOL_MIN_SIZE` | No | `2` | `app/db.py` | Minimum connection pool size. |
| `DATABASE_POOL_MAX_SIZE` | No | `10` | `app/db.py` | Maximum connection pool size — kept modest since this is a demo-scale deployment, not production traffic. |
| `DATABASE_SSL_MODE` | Yes in production | `require` | `app/db.py` | Alibaba RDS requires SSL by default; set to `disable` only for local dev against a non-SSL local Postgres. |

**Security note:** `DATABASE_URL` contains credentials inline. Never commit `.env` to the repo — `.gitignore` must include it, and `.env.example` (Section 17) ships with placeholder values only.

---

## 5. Alibaba Cloud — Deployment

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `ALIBABA_ACCESS_KEY_ID` | Yes | — | `deployment/proof/deployment_verification.py` | Alibaba Cloud SDK credential — used by the deployment proof script to make a real, verifiable API call (e.g. ECS `DescribeInstances`). |
| `ALIBABA_ACCESS_KEY_SECRET` | Yes | — | Same | Paired secret for the above. |
| `ALIBABA_REGION` | Yes | `ap-southeast-1` | Same, and `ecs-setup.md` provisioning | Region for ECS/Function Compute deployment. Choose based on lowest latency to your primary demo audience/judges, not necessarily proximity to South Africa given this is a hackathon demo, not GridFreeHub production. |
| `ALIBABA_ECS_INSTANCE_ID` | Yes if using ECS | — | `deployment_verification.py` | The specific instance ID the proof script targets — makes the proof concrete and checkable, not a generic "we have an account" claim. |
| `ALIBABA_FC_SERVICE_NAME` | Yes if using Function Compute instead of ECS | — | `function-compute.yaml` | Service name if the serverless deployment path is chosen instead of ECS. |
| `ALIBABA_RDS_INSTANCE_ID` | Yes | — | `rds-postgres-setup.md` | Identifies the managed Postgres instance backing `DATABASE_URL` in production — referenced in the deployment proof recording to show the database itself, not just the compute, runs on Alibaba Cloud. |
| `ALIBABA_OSS_BUCKET` | Optional | — | Only if using OSS for any static asset storage (e.g. serving the architecture diagram image) | Object storage bucket name, if used. |

**Security note:** these credentials grant real cloud account access — scope the IAM policy attached to this access key to the minimum required (ECS describe/read, RDS connect, and whatever the deployment proof script needs) rather than using full account admin credentials for a hackathon demo.

---

## 6. Memory Engine Tuning

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `MAX_MEMORY_TOKENS` | No | `800` | `memory/retrieval.py` | Hard cap on typed-memory context injected per response — the literal enforcement of "limited context window" from the track requirement. |
| `FALLBACK_BUDGET_TOKENS` | No | `150` | `memory/embeddings.py` | Separate, smaller cap for the hybrid retrieval fallback (Memory Design Doc §13) — deliberately kept small so fallback content can supplement but never dominate the prompt. |
| `DECAY_LAMBDA_PREFERENCE` | No | `0.01` | `memory/decay.py`, `memory/stability.py` | Base decay rate for `preference`-type memories before importance modulation. |
| `DECAY_LAMBDA_FACT` | No | `0.01` | Same | Base decay rate for `fact`-type memories. |
| `DECAY_LAMBDA_OUTCOME` | No | `0.05` | Same | Base decay rate for `outcome`-type memories — faster by design, per Memory Design Doc §2. |
| `DECAY_LAMBDA_CORRECTION` | No | `0.02` | Same | Base decay rate for `correction`-type memories, after the 14-day floor period expires. |
| `CORRECTION_FLOOR_DAYS` | No | `14` | `memory/decay.py` | Minimum days a `correction` memory stays above the surface threshold regardless of decay, per Memory Design Doc §4. |
| `CONFIDENCE_SURFACE_THRESHOLD` | No | `0.5` | `memory/retrieval.py` | Below this effective confidence, a memory is excluded from retrieval ranking entirely — the literal "forgetting" cutoff. |
| `CONFIDENCE_HIGH_TIER_THRESHOLD` | No | `0.85` | `chat/volta_prompt.py` | Above this, memories are phrased plainly (Memory Design Doc §8). |
| `STABILITY_GROWTH_BASE` | No | `1.5` | `memory/stability.py` | Base of the exponential stability growth per reinforcement, before importance modulation (Memory Design Doc §12). |
| `STABILITY_GROWTH_IMPORTANCE_RANGE` | No | `1.0` | Same | The additional range added to `STABILITY_GROWTH_BASE` scaled by importance_score — together producing the 1.5–2.5 growth factor range specified in the design doc. |
| `S0_DEFAULT` | No | `1.0` | `memory/stability.py` | Initial stability value (in days) before any reinforcement. |

---

## 7. Hybrid Retrieval & Embeddings

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `HYBRID_RETRIEVAL_ENABLED` | No | `true` | `memory/retrieval.py` | Feature flag — allows disabling the fallback path entirely for a simpler benchmark run comparing pure-typed-memory performance in isolation. |
| `HYBRID_SIMILARITY_THRESHOLD` | No | `0.6` | `memory/embeddings.py` | Cosine similarity floor below which the fallback search triggers, per Memory Design Doc §13. |
| `EMBEDDING_DIMENSION` | No | `1536` | `memory/embeddings.py` | Dimensionality of the vector index — must match whatever `QWEN_MODEL_EMBEDDING` actually outputs; verify against the provider's documentation rather than assuming. |
| `VECTOR_INDEX_BACKEND` | No | `pgvector` | `memory/embeddings.py` | Which vector search implementation is used — `pgvector` keeps everything in the same Postgres instance as the typed memory store, avoiding a second database dependency for a hackathon-scale deployment. |

---

## 8. Adversarial Defence & Plausibility

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `PLAUSIBILITY_CHECK_ENABLED` | No | `true` | `memory/plausibility.py` | Feature flag for the adversarial defence gate (Memory Design Doc §15). |
| `PLAUSIBILITY_CONFIDENCE_CAP` | No | `0.3` | `memory/plausibility.py` | Maximum `base_confidence` allowed for any observation flagged `boundary_violation`. |
| `DOMAIN_CONSTRAINTS_FILE` | Yes if plausibility check enabled | `config/domain_constraints.yaml` | `memory/plausibility.py` | Path to the domain-specific plausibility rules (plausible bill ranges, system sizes, prohibited claim patterns) referenced in the plausibility check prompt. |

---

## 9. Consolidation Cycle

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `CONSOLIDATION_ENABLED` | No | `true` | `memory/consolidation.py` | Feature flag. |
| `CONSOLIDATION_SESSION_INTERVAL` | No | `5` | `memory/consolidation.py` | Number of completed sessions between consolidation runs, per Memory Design Doc §17. |
| `CONSOLIDATION_STALENESS_DAYS` | No | `21` | `memory/consolidation.py` | Minimum age before a low-confidence memory becomes eligible for consolidation clustering. |

---

## 10. Eval Harness

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `EVAL_PERSONA_DIR` | No | `backend/eval/personas/` | `eval/run_eval.py` | Path to the 20 scripted persona YAML files. |
| `EVAL_RESULTS_OUTPUT` | No | `BENCHMARKS.md` | `eval/run_eval.py` | Where the auto-generated results table is written — kept at repo root per Directory Structure Doc §9 so it's immediately visible. |
| `EVAL_SYSTEM_VARIANTS` | No | `A,B,C,D` | `eval/run_eval.py` | Comma-separated list of which baseline systems to run in a given eval pass — useful for quick iteration (running only `D` while developing) versus full comparative runs (`A,B,C,D`) for the actual submission benchmarks. |
| `EVAL_RUN_ADVERSARIAL` | No | `true` | `eval/run_eval.py` | Whether to include the adversarial persona (Memory Design Doc §15.2) in a given run. |
| `IMPORTANCE_VALIDATION_DATASET` | No | `backend/eval/importance_validation_labels.json` | `eval/importance_validation.py` | Path to the 40-item human-labeled importance benchmark (Memory Design Doc §11.3). |

---

## 11. Explainability

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `EXPLAINABILITY_ENABLED` | No | `true` | `chat/volta_prompt.py`, `memory/explainability.py` | Feature flag for the `[EXPLAIN]` trailing block generation, per Memory Design Doc §16. Disabling saves tokens/cost per response but removes the trace shown in the deep-dive video. |
| `EXPLAIN_BLOCK_MAX_TOKENS` | No | `120` | `chat/volta_prompt.py` | Token budget reserved specifically for the explain block, kept separate from the main response budget so explainability doesn't crowd out the actual answer. |

---

## 12. Application & Server

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `APP_ENV` | Yes | `development` | `app/config.py` | `development` / `staging` / `production` — gates behaviour like verbose error responses (dev only) and which `.env` values are treated as required-strict vs warn-only. |
| `APP_PORT` | No | `8000` | `app/main.py` | Port the FastAPI server binds to. |
| `APP_HOST` | No | `0.0.0.0` | `app/main.py` | Bind address — `0.0.0.0` required for the Alibaba-hosted deployment to be reachable externally. |
| `CORS_ALLOWED_ORIGINS` | Yes in production | `http://localhost:3000` | `app/main.py` | Comma-separated allowed origins for the frontend to call the API — must include the hosted live demo's actual frontend URL once deployed (Section 13). |
| `SESSION_IDLE_TIMEOUT_MINUTES` | No | `30` | `chat/session.py` | How long a session can sit inactive before it's treated as ended and memory extraction is triggered automatically — relevant since the demo uses an explicit "end session" button but a real deployment needs an idle fallback. |

---

## 13. Hosted Live Demo

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `LIVE_DEMO_URL` | Yes (once deployed) | — | README, submission text description | The durable public URL judges and the community can test directly, per Directory Structure Doc §11 and Productization Doc §8. |
| `LIVE_DEMO_RATE_LIMIT_PER_IP` | Yes | `20` | `deployment/live-demo/rate-limiting.py` | Max requests per IP per hour on the public instance — prevents cost-exhaustion abuse of the shared Qwen API key during the public judging period. |
| `LIVE_DEMO_DEMO_ENTITY_RESET_HOURS` | No | `24` | `deployment/live-demo/rate-limiting.py` | How often the public demo's memory store for anonymous visitors is reset, so one visitor's test data doesn't permanently pollute the shared instance for the next. |

**Security note:** the hosted demo shares one `QWEN_API_KEY` across all public visitors — the rate limit above exists specifically to bound cost exposure from that shared key during the judging window.

---

## 14. Frontend

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | Yes | `http://localhost:8000` | `frontend/app/page.tsx`, all frontend API calls | Points the chat UI and memory transparency view at the backend — must be updated to the deployed Alibaba-hosted URL for the live demo build. |
| `NEXT_PUBLIC_DEMO_ENTITY_ID` | No | `demo-consumer-1` | Frontend | Default entity ID pre-filled for anonymous public demo visitors. |
| `NEXT_PUBLIC_ENABLE_TRANSPARENCY_VIEW` | No | `true` | `frontend/app/memory/page.tsx` | Toggles visibility of the memory transparency view in the public build — should stay `true` since it's core to the submission's proof strategy, but flagged here in case a judge-only vs public-facing build distinction is ever needed. |

---

## 15. Package Publishing (Standalone Library)

Relevant only to the `volta-memory-core` standalone package (Productization Doc §2), not the demo application itself.

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `PYPI_API_TOKEN` | Yes, for publishing | — | CI/CD publish workflow, not runtime | Auth token for publishing the package to PyPI. Never used by the application at runtime — only by the release pipeline. |
| `PACKAGE_VERSION` | Yes, for publishing | Semantic version string, e.g. `0.1.0` | `pyproject.toml`, release workflow | Version bumped per release per standard semver practice. |

**Security note:** `PYPI_API_TOKEN` should be scoped to the specific `volta-memory` project on PyPI, not an account-wide token, and stored only in CI secrets — never in any `.env` file that could be checked out locally by a contributor.

---

## 16. Observability & Logging

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | `app/config.py`, all modules | Standard logging verbosity. `DEBUG` recommended while developing the decay/retrieval logic, since seeing exact scores computed per candidate memory is the fastest way to verify correctness. |
| `LOG_REDACT_API_KEYS` | Yes | `true` | `app/config.py` | Must remain `true` in every environment — ensures `QWEN_API_KEY`, `OPENAI_API_KEY`, and Alibaba credentials never appear in any log line, including startup config dumps. |
| `COST_TRACKING_ENABLED` | No | `true` | `chat/qwen_client.py`, `eval/metrics.py` | Whether per-call token usage and cost are recorded — required for the eval harness's cost-per-session metric (Memory Design Doc §14.3) and the production unit-economics framing referenced throughout this suite. |

---

## 17. Full .env.example File

```bash
# ============================================
# Volta Memory — Environment Configuration
# Copy to .env and fill in real values.
# Never commit .env to the repository.
# ============================================

# --- Qwen Cloud (Section 2) ---
QWEN_API_KEY=
QWEN_API_BASE_URL=https://dashscope.aliyuncs.com/api/v1
QWEN_MODEL_CHAT=qwen-max
QWEN_MODEL_EXTRACTION=qwen-plus
QWEN_MODEL_EMBEDDING=text-embedding-v2
QWEN_MAX_RETRIES=3
QWEN_TIMEOUT_SECONDS=30

# --- Alternative LLM Backends (Section 3) ---
OPENAI_API_KEY=
OPENAI_MODEL_CHAT=gpt-4o-mini
LLM_BACKEND_DEFAULT=qwen

# --- Database (Section 4) ---
DATABASE_URL=postgresql://volta:changeme@localhost:5432/volta_memory
DATABASE_POOL_MIN_SIZE=2
DATABASE_POOL_MAX_SIZE=10
DATABASE_SSL_MODE=disable

# --- Alibaba Cloud (Section 5) ---
ALIBABA_ACCESS_KEY_ID=
ALIBABA_ACCESS_KEY_SECRET=
ALIBABA_REGION=ap-southeast-1
ALIBABA_ECS_INSTANCE_ID=
ALIBABA_FC_SERVICE_NAME=
ALIBABA_RDS_INSTANCE_ID=
ALIBABA_OSS_BUCKET=

# --- Memory Engine Tuning (Section 6) ---
MAX_MEMORY_TOKENS=800
FALLBACK_BUDGET_TOKENS=150
DECAY_LAMBDA_PREFERENCE=0.01
DECAY_LAMBDA_FACT=0.01
DECAY_LAMBDA_OUTCOME=0.05
DECAY_LAMBDA_CORRECTION=0.02
CORRECTION_FLOOR_DAYS=14
CONFIDENCE_SURFACE_THRESHOLD=0.5
CONFIDENCE_HIGH_TIER_THRESHOLD=0.85
STABILITY_GROWTH_BASE=1.5
STABILITY_GROWTH_IMPORTANCE_RANGE=1.0
S0_DEFAULT=1.0

# --- Hybrid Retrieval & Embeddings (Section 7) ---
HYBRID_RETRIEVAL_ENABLED=true
HYBRID_SIMILARITY_THRESHOLD=0.6
EMBEDDING_DIMENSION=1536
VECTOR_INDEX_BACKEND=pgvector

# --- Adversarial Defence & Plausibility (Section 8) ---
PLAUSIBILITY_CHECK_ENABLED=true
PLAUSIBILITY_CONFIDENCE_CAP=0.3
DOMAIN_CONSTRAINTS_FILE=config/domain_constraints.yaml

# --- Consolidation Cycle (Section 9) ---
CONSOLIDATION_ENABLED=true
CONSOLIDATION_SESSION_INTERVAL=5
CONSOLIDATION_STALENESS_DAYS=21

# --- Eval Harness (Section 10) ---
EVAL_PERSONA_DIR=backend/eval/personas/
EVAL_RESULTS_OUTPUT=BENCHMARKS.md
EVAL_SYSTEM_VARIANTS=A,B,C,D
EVAL_RUN_ADVERSARIAL=true
IMPORTANCE_VALIDATION_DATASET=backend/eval/importance_validation_labels.json

# --- Explainability (Section 11) ---
EXPLAINABILITY_ENABLED=true
EXPLAIN_BLOCK_MAX_TOKENS=120

# --- Application & Server (Section 12) ---
APP_ENV=development
APP_PORT=8000
APP_HOST=0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:3000
SESSION_IDLE_TIMEOUT_MINUTES=30

# --- Hosted Live Demo (Section 13) ---
LIVE_DEMO_URL=
LIVE_DEMO_RATE_LIMIT_PER_IP=20
LIVE_DEMO_DEMO_ENTITY_RESET_HOURS=24

# --- Frontend (Section 14) ---
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_DEMO_ENTITY_ID=demo-consumer-1
NEXT_PUBLIC_ENABLE_TRANSPARENCY_VIEW=true

# --- Package Publishing (Section 15) — CI only, not local runtime ---
PYPI_API_TOKEN=
PACKAGE_VERSION=0.1.0

# --- Observability & Logging (Section 16) ---
LOG_LEVEL=INFO
LOG_REDACT_API_KEYS=true
COST_TRACKING_ENABLED=true
```

---

## 18. Secrets Handling & Security Notes

**Never commit real values.** `.env` is git-ignored; `.env.example` (Section 17) ships with empty or placeholder values only, and is the only environment file tracked in the repository.

**Redaction is not optional.** `LOG_REDACT_API_KEYS=true` must be enforced in every environment, including local development — the habit of "I'll just leave verbose logging on locally" is exactly how a key ends up in a screen-recording taken for the demo video. Given this project's entire submission strategy involves recording screens repeatedly (Documents 06 and its addendum), this is a genuine, non-theoretical risk worth calling out explicitly rather than assuming.

**Scope cloud credentials minimally.** The Alibaba IAM policy attached to `ALIBABA_ACCESS_KEY_ID` should grant only what the deployment proof script and the application's actual runtime needs (ECS describe, RDS connect) — not account-wide administrative access, which is both a security best practice and, if a judge inspects the deployment proof script, a signal of engineering maturity rather than hackathon shortcuts.

**Rotate before and after the public demo window.** Because `LIVE_DEMO_URL` (Section 13) exposes a shared `QWEN_API_KEY` to public traffic for the duration of judging, rotate that key immediately after the judging period closes, regardless of whether `LIVE_DEMO_RATE_LIMIT_PER_IP` appeared to hold.

---

## 19. Per-Environment Variable Matrix

| Variable group | Local dev | CI (eval harness runs) | Production (Alibaba-hosted) |
|----------------|-----------|------------------------|------------------------------|
| Qwen Cloud | Required | Required | Required |
| Alternative backends | Optional | Required (for third-example CI check) | Optional |
| Database | Local Postgres | Ephemeral test DB | Alibaba RDS, `DATABASE_SSL_MODE=require` |
| Alibaba Cloud creds | Not needed | Not needed | Required |
| Memory tuning | Defaults fine | Explicit values recommended for reproducible eval runs | Defaults fine, tune post-launch with real usage data |
| Eval harness | Optional | Required | Not applicable |
| Live demo | Not applicable | Not applicable | Required |
| Package publishing | Not applicable | Required (release workflow only) | Not applicable |
| Logging | `DEBUG` recommended | `INFO` | `INFO`, `LOG_REDACT_API_KEYS=true` strictly enforced |


---

# ADDENDUM — Variables for Final Push Features
**Added: June 2026**

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `POPULATION_PRIORS_ENABLED` | No | `true` | `memory/population_priors.py` | Feature flag for cold-start priors (Design Doc §18) |
| `POPULATION_MIN_CONTRIBUTOR_COUNT` | Yes | `20` | Same | Privacy floor — patterns from fewer contributing entities are never written |
| `POPULATION_PRIOR_CONFIDENCE` | No | `0.35` | Same | Starting confidence for a population-seeded provisional memory — deliberately low |
| `CLARIFICATION_IMPORTANCE_THRESHOLD` | No | `0.7` | `memory/clarification.py` | Importance floor above which low confidence triggers active clarification rather than a soft hedge |
| `REPLAY_ENABLED` | No | `true` | `memory/replay.py` | Feature flag for the memory replay/dreaming cycle |
| `REPLAY_SAMPLE_SIZE` | No | `5` | Same | Number of old memories re-scored per replay cycle |
| `REPLAY_DRIFT_THRESHOLD` | No | `0.2` | Same | Minimum importance-score change required to write a reassessment |
| `META_MEMORY_ENABLED` | No | `true` | `memory/meta_memory.py` | Feature flag for known-gap tracking |
| `META_MEMORY_DOMAIN_CONFIG` | Yes if enabled | `config/expected_topics.yaml` | Same | Path to the per-domain expected-topic checklist |
| `SELF_TUNING_ENABLED` | No | `false` | `eval/self_tuning.py` | Off by default — an expensive grid search, run deliberately for the submission's final benchmark pass, not on every CI run |
| `SELF_TUNING_GRID_SIZE` | No | `27` | Same | Number of lambda/growth-factor combinations tested per search |
| `CHAOS_TESTING_ENABLED` | No | `false` | `eval/chaos/*` | Off by default in normal runs; enabled explicitly for the chaos-testing report |
| `CONCURRENCY_STRESS_ENTITY_COUNT` | No | `100` | `eval/concurrency/isolation_stress_test.py` | Number of simultaneous synthetic entities used in the isolation stress test |


---

# ADDENDUM — MCP, Tool-Calling, Streaming, and Token Budget Variables
**Added: June 2026**

| Variable | Required | Default | Used in | Description |
|----------|----------|---------|---------|-------------|
| `MCP_SERVER_ENABLED` | No | `true` | `mcp/volta_memory_server.py` | Feature flag for the MCP server |
| `MCP_TRANSPORT` | No | `stdio` | Same | `stdio` or `http` — which MCP transport mode the server runs |
| `MCP_SERVER_PORT` | Yes if `MCP_TRANSPORT=http` | `9000` | Same | Port for HTTP-transport MCP server |
| `NATIVE_TOOL_CALLING_ENABLED` | No | `true` | `chat/dialogue_tools.py` | Feature flag for Qwen native tool-calling on the dialogue-action decision |
| `STREAMING_ENABLED` | No | `true` | `chat/streaming.py` | Feature flag for SSE streaming responses |
| `EVAL_INCLUDE_MCP_VARIANT` | No | `true` | `eval/mcp_vs_injection_benchmark.py` | Whether the eval harness runs includes System E (MCP agent-directed) alongside A/B/C/D |

---

## 20. Token Budget Planning — Hackathon Credit Allocation

Given the Qwen Cloud free-trial credit is finite and this project's eval harness, self-tuning search, chaos testing, and public live demo all consume real tokens, this section exists to force an explicit budget check before running the full suite, not discover a shortfall mid-hackathon.

| Activity | Approx. calls | Est. tokens/call | Est. total tokens |
|----------|---------------|-------------------|--------------------|
| Core 3-session demo (recording) | ~15 | 500 | 7,500 |
| Eval harness, systems A–D, 20 personas × 3 sessions | ~240 | 600 | 144,000 |
| Eval harness, System E (MCP variant) | ~60 | 600 | 36,000 |
| Self-tuning grid search (27 combos × 20 personas, reduced session count) | ~540 | 400 | 216,000 |
| Chaos/concurrency testing | ~100 | 300 | 30,000 |
| Human eval study (8–12 participants × 2 variants) | ~40 | 500 | 20,000 |
| Public live demo (rate-limited, judging window) | Variable, capped by `LIVE_DEMO_RATE_LIMIT_PER_IP` | 500 | Bounded, monitor actual usage daily |

**Action before running the full suite:** total the known free-trial credit allocation and compare against the ~450,000+ token estimate above (excluding the variable live-demo pool). If tight, the self-tuning grid search (highest individual cost, lowest scoring leverage per the earlier priority ranking) is the first candidate to reduce in scope — cut the grid size or persona count for that specific run before cutting anything from the core eval harness or demo recordings, which carry more direct scoring weight.

