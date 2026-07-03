"""Postgres connection pool — local Postgres in dev, Alibaba RDS in production."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings

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
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


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
