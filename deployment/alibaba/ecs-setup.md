# Alibaba Cloud ECS — Volta Memory Backend

Step-by-step notes for provisioning an ECS instance to host the FastAPI backend.

## 1. Choose region

Set `ALIBABA_REGION` (default `ap-southeast-1`) based on demo audience latency.

## 2. Create ECS instance

- Image: Ubuntu 22.04 LTS
- Instance type: `ecs.t6-c1m2.large` or similar (hackathon demo scale)
- Public IP: assign elastic IP for stable `LIVE_DEMO_URL`
- Security group inbound:
  - TCP 22 (SSH, your IP only)
  - TCP 8000 or 443 (API, restricted during setup; open for judges when ready)

## 3. Install runtime

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
```

## 4. Deploy application

```bash
git clone <repo-url> volta-memory
cd volta-memory
cp .env.example .env
# Set QWEN_API_KEY, DATABASE_URL (RDS), DATABASE_SSL_MODE=require, CORS_ALLOWED_ORIGINS
docker compose up -d --build backend
```

## 5. Verify

```bash
curl http://<public-ip>:8000/health
python deployment/proof/deployment_verification.py
```

## 6. Record deployment proof

Capture a 30–60s screen recording showing ECS console, running process, and live `curl` response (see `docs/07_Submission_Checklist.md`).
