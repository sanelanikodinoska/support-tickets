"""
Lakebase (Databricks-managed Postgres) connection helper.

Production: reads LAKEBASE_URL from Databricks secret scope "database/lakebase-url"
Local dev:  reads LAKEBASE_URL from a .env file (copy .env.example → .env)

Single-URL pattern — no token refresh needed (native Postgres role, static password).
"""

import base64
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_SCOPE = os.environ.get("LAKEBASE_SECRET_SCOPE", "database")
_KEY   = os.environ.get("LAKEBASE_SECRET_KEY",   "lakebase-url")


def _lakebase_url() -> str:
    """Resolve the Lakebase connection URL.

    Priority:
    1. DATABRICKS_POSTGRES_CONNECTION_STRING_DATABASE (Apps V2 resource)
    2. LAKEBASE_URL env var  (local dev / .env)
    3. Databricks secret scope  (notebook testing)
    """
    # Apps V2: When you configure a 'database' resource in app.yaml,
    # Databricks automatically injects this environment variable
    url = os.environ.get("DATABRICKS_POSTGRES_CONNECTION_STRING_DATABASE")
    if url:
        return url
    
    # Local dev: .env file
    url = os.environ.get("LAKEBASE_URL")
    if url:
        return url

    # Notebook testing: Databricks secrets
    try:
        from databricks.sdk import WorkspaceClient
        _w = WorkspaceClient()
        secret = _w.secrets.get_secret(scope=_SCOPE, key=_KEY)
        return base64.b64decode(secret.value).decode("utf-8")
    except Exception as e:
        raise RuntimeError(
            "No Lakebase connection found. In Apps V2, ensure app.yaml has a 'database' resource. "
            f"For local dev, set LAKEBASE_URL in .env. Error: {e}"
        )


@contextmanager
def get_connection():
    """Yield a psycopg2 connection (RealDictCursor, auto-closed)."""
    conn = psycopg2.connect(_lakebase_url(), cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def run_query(sql: str, params=None) -> list[dict]:
    """Execute a SELECT and return rows as list[dict]."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def run_write(sql: str, params=None) -> int:
    """Execute INSERT/UPDATE/DELETE and return affected row count."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount


def run_write_returning(sql: str, params=None) -> dict:
    """Execute INSERT/UPDATE with RETURNING and return first row as dict."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            row = cur.fetchone()
            return dict(row) if row else {}
