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
        
    migrations_sql_path = repo_root / "backend" / "migrations" / "001_initial.sql"
    if not migrations_sql_path.exists():
        print(f"Error: Migrations script not found at {migrations_sql_path}")
        return 1
        
    print(f"Reading migrations from {migrations_sql_path.name}...")
    with open(migrations_sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
        
    print("Connecting to database...")
    try:
        # Use autocommit=True because CREATE EXTENSION cannot run in a transaction block
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                print("Applying schema migrations...")
                cur.execute(sql)
                print("[SUCCESS] Migrations applied successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to run migrations: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
