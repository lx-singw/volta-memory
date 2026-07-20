# Volta Memory Architecture

## Target production topology

```text
Browser
  |
  +-- HTTPS --> OSS + CDN (static Next.js export, runtime-config.js)
                    |
                    +-- HTTPS --> API Gateway
                                      |- exact CORS allowlist
                                      |- route-level rate/concurrency limits
                                      |- request and error access logs
                                      v
                                Function Compute 3.0 (FastAPI)
                                      |- Qwen Cloud: chat, extraction,
                                      |  relationship classification, embeddings
                                      |- RDS PostgreSQL + pgvector: sessions,
                                      |  messages, memories, provenance, relations
                                      `- SLS: request and application telemetry

Secrets Manager -> release process / least-privilege RAM role -> Function Compute
```

`runtime-config.js` holds only the public API and app origins plus CSRF identifier names. It is written before the static build, served with `no-store`, and is rejected if it points to localhost in production.

## Memory lifecycle

1. A user message is stored with a session and turn index.
2. Qwen extraction proposes typed observations with source evidence.
3. The service verifies a source quote against the original user message.
4. A new observation is stored, reinforced, or supersedes an active memory.
5. Provenance, relation, and lifecycle records make the transition auditable.
6. Retrieval packs only active, high-value memory into the response budget.
7. The response trace separates evidence used in the answer from retained or excluded information.

## Deployment status

The repository presently exposes a Function Compute verification URL listed in [README.md](README.md). The intended public topology is OSS/CDN plus API Gateway; the release is not considered cut over until the gateway origin, CDN origin, exact CORS allowlist, Function Compute role, SLS logging, and smoke tests are all configured as described in [production operations](deployment/alibaba/production-operations.md).

## Operational boundaries

- Function Compute is the only service that receives Qwen and database credentials.
- Static assets never contain secrets or a localhost production fallback.
- API Gateway, not a hidden UI button, is the first request-rate boundary for public traffic.
- The immutable showcase has a read-only API surface; user trials operate in isolated workspaces.
- Evaluation artifacts are generated from raw aggregate data and have a checksum; slides and reports consume that artifact rather than copying metric strings.
