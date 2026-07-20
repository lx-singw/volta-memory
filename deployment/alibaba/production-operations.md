# Alibaba Cloud Production Operations

## Target topology

The release topology is **OSS + CDN (static app) -> API Gateway -> Function Compute 3.0 -> RDS PostgreSQL + pgvector**. Qwen is called only from Function Compute. SLS receives request/application logs. The current FC verification URL is not the final public edge.

## One-time cloud configuration

1. Create a dedicated RAM role for Function Compute. Grant it only the resource ARNs it needs for SLS log delivery and approved secret access. Do not attach account-wide administrator access.
2. Put Qwen, database, `AUTH_SESSION_SECRET`, `ADMIN_API_KEY`, and any passwordless-email webhook token in Alibaba Cloud Secrets Manager, then inject them into the protected release environment. This repository never writes those values to `runtime-config.js` or logs them during deployment. `AUTH_SESSION_SECRET` must be a high-entropy value stable across Function Compute instances; rotating it invalidates outstanding browser sessions.
3. Configure a Function Compute `logConfig` (the checked-in `s.yaml` uses `auto` for first deployment) and confirm the function logstore has request and instance metrics. [FC logging guidance](https://help.aliyun.com/en/functioncompute/fc/user-guide/configure-the-logging-feature-1)
4. Configure API Gateway using [edge-policies.example.json](edge-policies.example.json) as an operator checklist. Bind the custom API domain, exact CORS origin, route-level rate limit, and concurrency limit. Alibaba documents route-level throttling and 429 behavior in its [API Gateway guide](https://help.aliyun.com/en/api-gateway/cloud-native-api-gateway/user-guide/configure-a-throttling-policy).
5. Configure OSS static website/CDN for the application domain. Upload static assets with the cache policy in `scripts/upload_frontend.py`; `runtime-config.js` and HTML must not be cached indefinitely.

## Release environment

```bash
export APP_ENV=production
export VOLTA_PUBLIC_APP_ORIGIN=https://app.example.com
export VOLTA_PUBLIC_API_BASE_URL=https://api.example.com
export CORS_ALLOWED_ORIGINS=https://app.example.com
export FC_RUNTIME_ROLE_ARN=acs:ram::<account-id>:role/volta-memory-fc-runtime
export FC_DISABLE_PUBLIC_INTERNET=true
export AUTH_SESSION_COOKIE_NAME=volta_session
export AUTH_CSRF_COOKIE_NAME=volta_csrf
export AUTH_COOKIE_DOMAIN=.example.com
export AUTH_SESSION_TTL_HOURS=336
export AUTH_MAGIC_LINK_BASE_URL=https://app.example.com
export AUTH_EMAIL_PROVIDER=alibaba_direct_mail
export CDN_INVALIDATION_COMMAND='aliyun cdn RefreshObjectCaches --ObjectPath https://app.example.com/index.html,https://app.example.com/runtime-config.js'
# Optional but strongly recommended: set ROLLBACK_COMMAND to an operator-reviewed
# command that restores the last known-good CDN version and Function Compute alias.
export ALIBABA_FC_ENDPOINT=<account-id>.ap-southeast-1.fc.aliyuncs.com
export ALIBABA_FC_FUNCTION_NAME=volta-memory-backend
export VOLTA_PUBLIC_HEALTH_URL=https://api.example.com/health
```

The Qwen key, `DATABASE_URL`, `AUTH_SESSION_SECRET`, `ADMIN_API_KEY`, and `AUTH_EMAIL_WEBHOOK_TOKEN` are also required by the Function Compute release but are intentionally omitted from examples. Source them from the release secret store. `AUTH_COOKIE_DOMAIN` must be the shared parent domain of the app and API hosts (for example `.example.com` for `app.example.com` and `api.example.com`). When email is enabled, set `AUTH_EMAIL_WEBHOOK_URL` to the trusted Direct Mail adapter endpoint; do not put Direct Mail credentials in the browser or repository.

## Release order

```bash
# Apply schema changes through the approved migration procedure first.
./migrate.sh

# Build and deploy Function Compute after gateway integration is ready.
s build --use-docker
python scripts/deploy_backend.py

# Build the static app only after the real public API origin is known.
python scripts/build_static_release.py
python scripts/upload_frontend.py
python scripts/configure_oss_website.py
```

`upload_frontend.py` requires `CDN_INVALIDATION_COMMAND` and runs it after upload for `index.html`, route HTML, and `runtime-config.js`, then runs deployed edge verification. Set `ROLLBACK_COMMAND` to an operator-reviewed restoration command for the last known-good CDN and Function Compute alias. Then run deployed smoke tests against the public app and API Gateway; never substitute a localhost result.

`build_static_release.py` runs `preflight_public_edge.py --api-only` after static validation. It blocks a build unless the configured API Gateway health responds and credentialed CORS accepts the exact app origin. `upload_frontend.py` then runs the full preflight after publication, verifying the actual CDN runtime config points at that gateway. This makes an unprovisioned or bypassed gateway a release failure rather than a documentation promise.

## Cutover and rollback

1. Verify gateway -> Function Compute health and a full chat/end-session workflow.
2. Set `FC_DISABLE_PUBLIC_INTERNET=true` so public traffic no longer reaches the direct FC trigger.
3. If the public smoke test fails, restore the prior known-good CDN version and Function Compute version/alias through the release console, then investigate through SLS request IDs. Do not expose the direct FC trigger as an emergency bypass.

## Proof recording

Install `backend[alibaba]`, export the proof variables above, and run:

```bash
python deployment/proof/deployment_verification.py
```

The script calls Function Compute through its SDK and checks the public health URL without printing credentials.
