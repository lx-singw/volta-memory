# Alibaba RDS Postgres (Serverless) — Volta Memory

Provisioning and configuration notes for the managed Postgres database backing `DATABASE_URL` in a Cloud-Native Serverless setup.

## 1. Create RDS Serverless Instance

- **Billing Method**: Select **Serverless** to allow compute capacity (RCUs) to scale dynamically (e.g., min `0.5 RCU` to max `2 RCU`).
- **Engine**: PostgreSQL 16
- **Edition**: Select **Basic Edition** or **High Availability Edition** (Single Zone is cost-optimized for hackathon).
- **Region**: Match the compute region (e.g., **Singapore / `ap-southeast-1`**).
- **Database name**: `volta_memory`

## 2. Privileges & Permissions (Important for PostgreSQL 15+)

In PostgreSQL 15+, the `public` schema has default write privileges removed. Only superusers (or `rds_superuser` roles) can create extensions. Use this aligned role configuration:

1. **Privileged Account (Superuser)**:
   - Create an account named `volta_admin` with account type **Privileged** (Superuser).
   - Use this account credentials for the initial extension provisioning.
2. **Normal Account (Database Owner)**:
   - Create an account named `volta` with account type **Normal**.
   - Create the `volta_memory` database and assign its owner to `volta`.
3. **Schema Grant**:
   - Connect to the `volta_memory` database as `volta_admin` and grant write privileges to `volta`:
     ```sql
     GRANT ALL ON SCHEMA public TO volta;
     ```
   - Connect your main application using the least-privilege `volta` user.

## 3. SSL Configuration

Alibaba Cloud RDS disables SSL by default. For secure transport:
1. Navigate to **Database Connection** in the RDS console.
2. Under the *Public Connection* section, click **Apply for Public Endpoint**.
3. Under **Whitelist and SecGroup**, modify the `default` whitelist to `0.0.0.0/0` (or your local IP).
4. Navigate to the SSL page and click **Modify SSL** to enable SSL for the public endpoint. Set `DATABASE_SSL_MODE=require` in your environment:

```properties
DATABASE_URL=postgresql://volta:PASSWORD@volta-db-gs5u65bd5p38lzot.pgsql.singapore.rds.aliyuncs.com:5432/volta_memory?sslmode=require
DATABASE_SSL_MODE=require
ALIBABA_RDS_INSTANCE_ID=pgm-gs5u65bd5p38lzot
```

## 4. Run Migrations

To apply the schema tables, vector structures, and indices securely:
```bash
# Run the migration script at the repository root
chmod +x migrate.sh
./migrate.sh
```

## 5. Verify Deployment

Run the verification script to check that the ECS/FC compute environment successfully connects to the running database instance and registers correctly with the Alibaba Cloud SDK:
```bash
python3 deployment/proof/deployment_verification.py
```

