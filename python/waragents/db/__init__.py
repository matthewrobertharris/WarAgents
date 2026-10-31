"""The PostgreSQL connection: a pool of connections, and transactions that nest.

The database is named by WARAGENTS_DATABASE_URL, such as
postgresql://waragents:secret@localhost:5432/waragents. It's read from the environment, or from a
.env file in the python folder (one NAME=value per line), so it doesn't have to be set by hand.

    db = Database(database_url())
    with db.transaction():      # everything inside commits together, or not at all
        db.execute("update players set xp = xp + %s where id = %s", (10, "alice"))
        rows = db.query("select id, xp from players")

A transaction started inside another one is a savepoint in it, so functions that need to be atomic
can start one without knowing whether their caller already has.
"""

from __future__ import annotations

import atexit
import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

PYTHON_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = PYTHON_DIR / ".env"
URL_VARIABLE = "WARAGENTS_DATABASE_URL"

__all__ = ["Database", "DatabaseNotReady", "Jsonb", "database_url", "load_env", "psycopg"]


class DatabaseNotReady(RuntimeError):
    """The database isn't configured, can't be reached, or hasn't been set up."""


def load_env(path: Path = ENV_FILE) -> None:
    """Add the NAME=value lines in a .env file to the environment. Variables that are already set
    win, so a real environment always overrides the file."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("'\""))


def database_url(variable: str = URL_VARIABLE) -> str:
    load_env()
    url = os.environ.get(variable)
    if not url:
        raise DatabaseNotReady(
            f"Set {variable} to the database's URL, for example "
            f"postgresql://waragents:password@localhost:5432/waragents, or put it in {ENV_FILE}")
    return url


class Database:
    def __init__(self, url: str, min_size: int = 1, max_size: int = 10):
        self.url = url
        self.pool = ConnectionPool(url, min_size=min_size, max_size=max_size, open=False,
                                   kwargs={"autocommit": True, "row_factory": dict_row})
        # The connection of the transaction this thread is in, if any.
        self._current: ContextVar[psycopg.Connection | None] = ContextVar(f"waragents-db-{id(self)}",
                                                                          default=None)
        atexit.register(self.close)  # the pool's threads can't be stopped once Python is shutting down
        try:
            self.pool.open(wait=True, timeout=10)
        except psycopg.OperationalError as e:
            raise DatabaseNotReady(f"Can't connect to the database: {e}") from e
        except Exception as e:  # the pool raises PoolTimeout when it can't connect in time
            raise DatabaseNotReady(f"Can't connect to the database at {_safe(url)}: {e}") from e

    def close(self) -> None:
        self.pool.close()

    @contextmanager
    def transaction(self) -> Iterator[psycopg.Connection]:
        conn = self._current.get()
        if conn is not None:
            with conn.transaction():  # a savepoint in the outer transaction
                yield conn
            return
        with self.pool.connection() as conn:
            token = self._current.set(conn)
            try:
                with conn.transaction():
                    yield conn
            finally:
                self._current.reset(token)

    def query(self, sql: str, params: Any = None) -> list[dict[str, Any]]:
        with self.transaction() as conn:
            return conn.execute(sql, params).fetchall()

    def one(self, sql: str, params: Any = None) -> dict[str, Any] | None:
        with self.transaction() as conn:
            return conn.execute(sql, params).fetchone()

    def value(self, sql: str, params: Any = None) -> Any:
        row = self.one(sql, params)
        return None if row is None else next(iter(row.values()))

    def execute(self, sql: str, params: Any = None) -> int:
        """Run a statement. Returns the number of rows it changed."""
        with self.transaction() as conn:
            return conn.execute(sql, params).rowcount


def _safe(url: str) -> str:
    """A database URL without its password, for messages."""
    try:
        info = psycopg.conninfo.conninfo_to_dict(url)
    except psycopg.ProgrammingError:
        return "the configured URL"
    return f"{info.get('host', 'localhost')}:{info.get('port', 5432)}/{info.get('dbname', '')}"
