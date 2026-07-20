"""Postgres connection pool — local Postgres in dev, Alibaba RDS in production."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import logging
import psycopg
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None


def _conninfo() -> str:
    settings = get_settings()
    url = settings.database_url
    if settings.database_ssl_mode != "disable" and "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode={settings.database_ssl_mode}"
    return url


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = ConnectionPool(
            conninfo=_conninfo(),
            min_size=0,
            max_size=settings.database_pool_max_size,
            kwargs={"row_factory": dict_row, "connect_timeout": 5},
            timeout=10,
        )
    return _pool


@contextmanager
def get_connection() -> Generator[Connection, None, None]:
    import time
    from psycopg_pool import PoolTimeout
    
    pool = get_pool()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            ctx = pool.connection()
            conn = ctx.__enter__()
            break
        except PoolTimeout as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to acquire db connection from pool after {max_retries} attempts: {e}")
                raise
            logger.warning(f"DB connection pool timeout: {e}. Retrying in 1.0s...")
            time.sleep(1.0)
            
    try:
        yield conn
    except BaseException as exc:
        # Forward exception details to psycopg's connection context manager so
        # it rolls back instead of committing a partially completed transaction.
        ctx.__exit__(type(exc), exc, exc.__traceback__)
        raise
    else:
        ctx.__exit__(None, None, None)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def check_database() -> bool:
    try:
        with psycopg.connect(_conninfo(), connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
