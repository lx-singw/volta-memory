# Public URL and Cutover Record

## Current verification endpoint

- Function Compute app: <https://volta-m-backend-mlutvrvuqy.ap-southeast-1.fcapp.run>
- Function Compute memory view: <https://volta-m-backend-mlutvrvuqy.ap-southeast-1.fcapp.run/memory>
- Function Compute health: <https://volta-m-backend-mlutvrvuqy.ap-southeast-1.fcapp.run/health>

These URLs verify the present FC deployment. They are not a claim that the OSS/CDN and API Gateway cutover has already completed.

## Required final public URLs

Before submission, record the real values in the release environment and in `SUBMISSION.md`:

```bash
VOLTA_PUBLIC_APP_ORIGIN=https://<cdn-app-domain>
VOLTA_PUBLIC_API_BASE_URL=https://<api-gateway-domain>
VOLTA_PUBLIC_HEALTH_URL=https://<api-gateway-domain>/health
CORS_ALLOWED_ORIGINS=https://<cdn-app-domain>
FC_DISABLE_PUBLIC_INTERNET=true
```

There must be no `example.com`, localhost, shared reset route, or direct Function Compute public URL in the judge-facing submission copy after cutover.
