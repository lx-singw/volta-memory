# Security and Public-Demo Boundaries

## Release invariants

- Production CORS is an exact HTTPS origin list. `*` is rejected by the deployment script.
- A static export is rejected when it contains a localhost API reference or an invalid `runtime-config.js` origin.
- `AUTH_COOKIE_DOMAIN` is required for the split `app.` / `api.` deployment and must be the shared parent domain; both session and CSRF cookies use it.
- The Qwen key, database URL, cloud credentials, and session secrets remain server-side. The runtime config contains only public origin and CSRF identifier metadata.
- Function Compute receives a dedicated RAM role. The role should grant only the required FC, SLS, Secret Manager, and network access—not account-wide administrator permissions.
- SLS receives structured runtime logs; request, model-cost, error-rate, and end-session failures must be monitored from there.
- API Gateway provides public request and concurrency throttling before Qwen work is started.

## Required cloud controls before public cutover

1. Store `QWEN_API_KEY`, database credentials, `AUTH_SESSION_SECRET`, `ADMIN_API_KEY`, and passwordless-email delivery tokens in Alibaba Cloud Secrets Manager or inject them into the release environment from an approved secret store. `AUTH_SESSION_SECRET` must be high entropy and stable across instances; `ADMIN_API_KEY` protects operational routes. Do not commit `.env` and do not print credentials during deployment.
2. Bind the gateway custom domain to Function Compute. Set `FC_DISABLE_PUBLIC_INTERNET=true` only after gateway routing is verified, so direct FC internet access cannot bypass edge policy.
3. Configure `CORS_ALLOWED_ORIGINS` with the exact OSS/CDN app domain and a separately approved preview domain if needed.
4. Configure API Gateway limits for public chat, session end, and all expensive endpoints. Return a JSON `429` response; limit both QPS and concurrency.
5. Configure the Function Compute RAM role and enable/confirm SLS logging. Do not use a personal AccessKey from function code.
6. Rotate Qwen and database credentials after the public judging period.

## Data boundaries

- Showcase data is read-only and exists only to demonstrate an auditable correction lineage.
- Trial and signed-in user workspaces are isolated by server-resolved identity; browser-supplied entity identifiers are not authorization.
- Export and permanent deletion are destructive account actions and require authenticated server-side authorization.
- Sanitized benchmark artifacts exclude conversations, provider payloads, and detailed error strings.

## Incident response

1. Disable the gateway route or reduce its rate policy if abuse or spend spikes.
2. Rotate the exposed service credential if a secret may have appeared in a log or recording.
3. Preserve SLS request IDs and lifecycle events for investigation; never edit the benchmark or memory audit record to conceal an incident.
4. Re-run deployed smoke tests before reopening public access.
