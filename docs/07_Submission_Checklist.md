# Submission Checklist (Current)

The authoritative final checklist is [SUBMISSION.md](../SUBMISSION.md). This shorter document exists for readers following the older numbered documentation set.

Before submitting:

1. Confirm the public repository, MIT license, live OSS/CDN URL, API Gateway health URL, architecture diagram, deck, and public video URL are filled in `SUBMISSION.md`.
2. Record the correction lifecycle from [DEMO_RUNBOOK.md](../DEMO_RUNBOOK.md) in one continuous deployed-browser flow.
3. Run `python deployment/proof/deployment_verification.py` with Function Compute proof variables and capture the non-sensitive output.
4. Verify `BENCHMARKS.md`, the JSON artifact, deck, README, and submission description use the same measured values.
5. Verify no direct FC URL, localhost fallback, reset route, secret, or admin workflow is presented as the public demo.
