"""Schema migrations: the numbered .sql files in migrations/, applied in order.

Each file runs in its own transaction and is recorded in schema_migrations, so running the
migrations again only applies the new ones. An advisory lock stops two servers migrating at once.
Never change a file that has been applied somewhere: add a new one.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import Database, DatabaseNotReady

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_FILE = re.compile(r"(\d{3})_[a-z0-9_]+\.sql")
_LOCK = 7_211_946  # any number, as long as nothing else uses it

_TRACKING = """
create table if not exists schema_migrations (
    version    integer primary key,
    name       text not null,
    applied_at timestamptz not null default now()
)"""


def available() -> list[tuple[int, Path]]:
    files = [(int(m.group(1)), p) for p in MIGRATIONS_DIR.glob("*.sql") if (m := _FILE.fullmatch(p.name))]
    return sorted(files)


def applied(db: Database) -> set[int]:
    exists = db.value("select to_regclass('schema_migrations') is not null")
    return {r["version"] for r in db.query("select version from schema_migrations")} if exists else set()


def pending(db: Database) -> list[tuple[int, Path]]:
    done = applied(db)
    return [(version, path) for version, path in available() if version not in done]


def migrate(db: Database) -> list[str]:
    """Apply every pending migration. Returns the names of the ones applied."""
    names = []
    with db.transaction() as conn:
        conn.execute("select pg_advisory_xact_lock(%s)", (_LOCK,))
        conn.execute(_TRACKING)
        done = {r["version"] for r in conn.execute("select version from schema_migrations").fetchall()}
        for version, path in available():
            if version in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("insert into schema_migrations (version, name) values (%s, %s)",
                             (version, path.name))
            names.append(path.name)
    return names


def require_current(db: Database) -> None:
    """Raise DatabaseNotReady unless every migration has been applied."""
    missing = pending(db)
    if missing:
        raise DatabaseNotReady(
            f"The database needs {len(missing)} migration(s), starting with {missing[0][1].name}. "
            "Run: python -m waragents.db setup")
