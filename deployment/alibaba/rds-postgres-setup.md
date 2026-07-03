# Alibaba RDS Postgres — Volta Memory

Provisioning notes for the managed Postgres backing `DATABASE_URL`.

## 1. Create RDS instance

- Engine: PostgreSQL 16
- Edition: High Availability optional for demo; Single Node acceptable for hackathon
- Enable **pgvector** extension support
- Database name: `volta_memory`
- Master user: `volta_app` (or separate app user)

## 2. Networking

- Place RDS in same VPC as ECS
- Security group: allow TCP 5432 from ECS security group only (not 0.0.0.0/0 in production)
- For local dev against RDS: temporarily whitelist your dev machine public IP

## 3. SSL

Alibaba RDS requires SSL. Set in `.env`:

```bash
DATABASE_URL=postgresql://volta_app:PASSWORD@pgm-xxxxx.pg.rds.aliyuncs.com:5432/volta_memory
DATABASE_SSL_MODE=require
ALIBABA_RDS_INSTANCE_ID=pgm-xxxxx
```

## 4. Apply schema

```bash
psql "$DATABASE_URL" -f backend/migrations/001_initial.sql
```

## 5. Verify pgvector

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

## 6. Deployment proof

Reference `ALIBABA_RDS_INSTANCE_ID` in the deployment verification recording to show the database runs on Alibaba Cloud, not just compute.
