# Volta Memory Submission Checklist

## Required links to fill before submitting

| Item | Final value | Gate |
|---|---|---|
| Public source repository | `TODO: public repository URL` | MIT license visible and repository clones without secrets |
| Live app | `TODO: OSS/CDN app URL` | opens in an incognito browser and never calls localhost |
| API health | `TODO: API Gateway /health URL` | returns healthy over HTTPS |
| Public video | `TODO: YouTube/Vimeo/Facebook URL` | public when logged out; approximately 3 minutes |
| Deck | `docs/volta_memory_deck.pptx` | generated from evaluation summary and visually checked |
| Architecture | `ARCHITECTURE.md`, `docs/architecture.svg` | shows OSS/CDN, API Gateway, FC, RDS, Qwen, SLS, and RAM/secret boundary |
| Benchmark evidence | `BENCHMARKS.md`, `backend/eval/artifacts/` | report checksum and final deck values agree |

## Track 1 statement

Volta Memory is submitted to **Track 1: MemoryAgent**. It addresses persistent cross-session memory through a typed store, timed forgetting through confidence decay, correction handling through supersession rather than deletion, and limited-context recall through budgeted retrieval. Its user-facing proof is source-linked evidence and an answer-level explanation trace.

## Submission description

Volta Memory is a Qwen-powered home-energy advisor that treats long-term memory as a governed decision layer rather than a transcript archive. At the end of a consultation, it extracts source-linked observations, verifies source evidence, and stores typed memory in PostgreSQL. When the user corrects a fact, Volta creates an auditable successor relation instead of silently overwriting history. At answer time, it retrieves only current, high-value memory into a limited context budget, excludes stale or irrelevant facts, and shows which evidence shaped the recommendation. The Memory Map, timeline, lifecycle receipt, and “Why this advice” panel make the decision path inspectable.

## Final release gate

- [ ] `python scripts/build_static_release.py` passes with actual HTTPS CDN and gateway origins.
- [ ] `python scripts/upload_frontend.py` passes static localhost validation.
- [ ] `CDN_INVALIDATION_COMMAND` and the operator-reviewed `ROLLBACK_COMMAND` are configured for the release.
- [ ] Function Compute uses the release RAM role and SLS logging.
- [ ] API Gateway has exact CORS, rate, and concurrency policies; direct FC public access is disabled after cutover.
- [ ] Showcase remains immutable and `/try` creates a separate workspace.
- [ ] The recorded correction sequence matches [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md).
- [ ] `BENCHMARKS.md`, evaluation JSON, deck, README, and Devpost text use the same metrics.
- [ ] Public video and all URLs have been opened while logged out.
