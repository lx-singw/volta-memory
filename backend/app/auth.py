"""Server-side workspace identity, CSRF, and passwordless account primitives."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException, Request, Response, status

from app.config import get_settings
from app.db import get_connection
from app.utils.clock import get_now


@dataclass(frozen=True)
class Workspace:
    entity_id: str
    entity_type: str
    is_read_only: bool
    user_id: UUID | None
    csrf_token: str
    csrf_hash: str


def _secret() -> bytes:
    settings = get_settings()
    if settings.app_env == "production" and not settings.auth_session_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workspace authentication is not configured.",
        )
    # Development fallback is intentionally not accepted in production.
    return (settings.auth_session_secret or "volta-development-only-session-secret").encode("utf-8")


def hash_secret(value: str) -> str:
    return hmac.new(_secret(), value.encode("utf-8"), hashlib.sha256).hexdigest()


def _set_workspace_cookies(response: Response, token: str, csrf_token: str) -> None:
    settings = get_settings()
    max_age = settings.auth_session_ttl_hours * 3600
    common = {
        "max_age": max_age,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
    }
    if settings.auth_cookie_domain:
        common["domain"] = settings.auth_cookie_domain
    response.set_cookie(
        settings.auth_session_cookie_name,
        token,
        httponly=True,
        **common,
    )
    response.set_cookie(
        settings.auth_csrf_cookie_name,
        csrf_token,
        httponly=False,
        **common,
    )


def clear_workspace_cookies(response: Response) -> None:
    settings = get_settings()
    kwargs: dict[str, str] = {"path": "/"}
    if settings.auth_cookie_domain:
        kwargs["domain"] = settings.auth_cookie_domain
    response.delete_cookie(settings.auth_session_cookie_name, **kwargs)
    response.delete_cookie(settings.auth_csrf_cookie_name, **kwargs)


def _insert_entity(connection: Any, entity_id: str, entity_type: str, user_id: UUID | None = None) -> None:
    connection.execute(
        """
        INSERT INTO entities (id, owner_user_id, entity_type, is_read_only)
        VALUES (%s, %s, %s, false)
        ON CONFLICT (id) DO NOTHING
        """,
        (entity_id, user_id, entity_type),
    )


def establish_workspace_session(
    response: Response,
    *,
    entity_id: str,
    entity_type: str,
    user_id: UUID | None = None,
) -> Workspace:
    """Issue a fresh opaque browser session after creating or claiming a workspace."""
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(24)
    now = get_now()
    expires_at = now + timedelta(hours=get_settings().auth_session_ttl_hours)
    with get_connection() as conn:
        _insert_entity(conn, entity_id, entity_type, user_id)
        conn.execute(
            """
            INSERT INTO auth_sessions (
                id, token_hash, csrf_token_hash, entity_id, user_id, expires_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (uuid4(), hash_secret(token), hash_secret(csrf_token), entity_id, user_id, expires_at),
        )
    _set_workspace_cookies(response, token, csrf_token)
    return Workspace(
        entity_id=entity_id,
        entity_type=entity_type,
        is_read_only=False,
        user_id=user_id,
        csrf_token=csrf_token,
        csrf_hash=hash_secret(csrf_token),
    )


def create_anonymous_workspace(response: Response) -> Workspace:
    return establish_workspace_session(
        response,
        entity_id=f"anon-{uuid4()}",
        entity_type="anonymous",
    )


def get_workspace(request: Request, response: Response) -> Workspace:
    """Resolve the entity exclusively from the opaque server-side cookie.

    A first visit receives a fresh isolated anonymous workspace, so browser callers
    never select another tenant by supplying an entity_id query parameter.
    """
    settings = get_settings()
    raw_token = request.cookies.get(settings.auth_session_cookie_name)
    raw_csrf = request.cookies.get(settings.auth_csrf_cookie_name)
    if not raw_token:
        return create_anonymous_workspace(response)

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT session.entity_id, session.user_id, session.csrf_token_hash,
                   entity.entity_type, entity.is_read_only
            FROM auth_sessions session
            JOIN entities entity ON entity.id = session.entity_id
            WHERE session.token_hash = %s
              AND session.revoked_at IS NULL
              AND session.expires_at > now()
            """,
            (hash_secret(raw_token),),
        ).fetchone()
        if row:
            csrf_token = raw_csrf
            csrf_hash = row["csrf_token_hash"]
            if not csrf_token or not hmac.compare_digest(hash_secret(csrf_token), csrf_hash):
                # Rotate missing/stale CSRF tokens without rotating the HttpOnly session.
                csrf_token = secrets.token_urlsafe(24)
                csrf_hash = hash_secret(csrf_token)
                conn.execute(
                    "UPDATE auth_sessions SET csrf_token_hash = %s, last_seen_at = now() WHERE token_hash = %s",
                    (csrf_hash, hash_secret(raw_token)),
                )
                _set_workspace_cookies(response, raw_token, csrf_token)
            else:
                conn.execute(
                    "UPDATE auth_sessions SET last_seen_at = now() WHERE token_hash = %s",
                    (hash_secret(raw_token),),
                )
            return Workspace(
                entity_id=row["entity_id"],
                entity_type=row["entity_type"],
                is_read_only=bool(row["is_read_only"]),
                user_id=row["user_id"],
                csrf_token=csrf_token,
                csrf_hash=csrf_hash,
            )

    return create_anonymous_workspace(response)


def require_csrf(request: Request, workspace: Workspace) -> None:
    provided = request.headers.get("X-CSRF-Token", "")
    if not provided or not hmac.compare_digest(provided, workspace.csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
    if not hmac.compare_digest(hash_secret(provided), workspace.csrf_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")


def require_admin(request: Request) -> None:
    settings = get_settings()
    supplied = request.headers.get("X-Admin-Key", "")
    if not settings.admin_api_key or not hmac.compare_digest(supplied, settings.admin_api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin authority is required.")


def create_magic_link(email: str, entity_id: str) -> tuple[str, str]:
    """Create a one-time opaque login token; delivery is handled separately."""
    token = secrets.token_urlsafe(32)
    now = get_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO auth_login_tokens (id, token_hash, email, entity_id, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                uuid4(),
                hash_secret(token),
                email.lower(),
                entity_id,
                now + timedelta(minutes=get_settings().auth_magic_link_ttl_minutes),
            ),
        )
    base = get_settings().auth_magic_link_base_url.rstrip("/")
    link = f"{base}/auth/verify?token={token}" if base else token
    return token, link


def deliver_magic_link(email: str, link: str) -> dict[str, str]:
    """Provider abstraction with a production-safe webhook adapter.

    A Direct Mail integration can be placed behind the configured signed webhook;
    raw provider credentials never enter the browser or repository.
    """
    settings = get_settings()
    provider = settings.auth_email_provider.lower()
    if provider in {"webhook", "alibaba_direct_mail"} and settings.auth_email_webhook_url:
        headers = {"Content-Type": "application/json"}
        if settings.auth_email_webhook_token:
            headers["Authorization"] = f"Bearer {settings.auth_email_webhook_token}"
        response = httpx.post(
            settings.auth_email_webhook_url,
            json={"to": email, "magicLink": link, "template": "volta-passwordless-login"},
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return {"delivery": provider}
    if settings.app_env != "production":
        return {"delivery": "development", "magicLink": link}
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Passwordless email delivery is not configured.",
    )


def consume_magic_link(token: str, response: Response) -> Workspace:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, email, entity_id
            FROM auth_login_tokens
            WHERE token_hash = %s AND consumed_at IS NULL AND expires_at > now()
            FOR UPDATE
            """,
            (hash_secret(token),),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This sign-in link is invalid or expired.")
        user = conn.execute(
            """
            INSERT INTO users (id, email) VALUES (%s, %s)
            ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
            RETURNING id
            """,
            (uuid4(), row["email"]),
        ).fetchone()
        entity_id = row["entity_id"] or f"user-{user['id']}"
        _insert_entity(conn, entity_id, "user", user["id"])
        conn.execute(
            """
            UPDATE entities SET owner_user_id = %s, entity_type = 'user', updated_at = now()
            WHERE id = %s AND is_read_only = false
            """,
            (user["id"], entity_id),
        )
        conn.execute("UPDATE auth_login_tokens SET consumed_at = now() WHERE id = %s", (row["id"],))

    return establish_workspace_session(
        response,
        entity_id=entity_id,
        entity_type="user",
        user_id=user["id"],
    )
