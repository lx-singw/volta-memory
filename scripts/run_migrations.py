#!/usr/bin/env python3
"""Run database schema migrations against the PostgreSQL instance."""

import os
import sys
from pathlib import Path
from dotenv import dotenv_values
import psycopg

def main() -> int:
    # Resolve .env path relative to this script's directory
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent
    env_path = repo_root / ".env"
    
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        return 1
        
    env = dotenv_values(env_path)
    db_url = env.get("DATABASE_URL")
    
    if not db_url:
        print("Error: DATABASE_URL not set in .env")
        return 1
        
    migrations_dir = repo_root / "backend" / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        print(f"Error: No migrations found in {migrations_dir}")
        return 1

    print("Connecting to database...")
    try:
        from psycopg.errors import DuplicateObject, DuplicateColumn, DuplicateTable, UniqueViolation
        # Use autocommit=True because CREATE EXTENSION cannot run in a transaction block
        with psycopg.connect(db_url, autocommit=True) as conn:
            for file_path in migration_files:
                print(f"Applying migration: {file_path.name}...")
                with open(file_path, "r", encoding="utf-8") as f:
                    sql = f.read()
                
                # Split SQL statements by semicolon and execute them one by one to avoid halting on a single duplicate constraint
                # Simple parsing by semicolon
                statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
                with conn.cursor() as cur:
                    for stmt in statements:
                        try:
                            cur.execute(stmt)
                        except (DuplicateObject, DuplicateColumn, DuplicateTable, UniqueViolation) as e:
                            print(f"  [WARNING] Handled duplicate in {file_path.name}: {e}")
                        except Exception as e:
                            print(f"  [ERROR] Statement failed: {stmt[:60]}... Error: {e}")
                            raise e
            print("[SUCCESS] All migrations applied successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to run migrations: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
