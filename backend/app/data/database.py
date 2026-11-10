from __future__ import annotations

import os
import sqlite3
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = BACKEND_ROOT / "data"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DATABASE_PATH = DATA_ROOT / "food_decision.db"


def resolve_database_path(database_path: str | Path | None = None) -> Path:
    if database_path is not None:
        return Path(database_path).resolve()

    configured_path = os.getenv("FOOD_DECISION_DB_PATH")
    if configured_path:
        return Path(configured_path).resolve()
    return DEFAULT_DATABASE_PATH


def connect_database(database_path: str | Path | None = None) -> sqlite3.Connection:
    path = resolve_database_path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_database(
    database_path: str | Path | None = None,
    *,
    reset: bool = False,
) -> Path:
    path = resolve_database_path(database_path)
    if reset and path.exists():
        path.unlink()

    with connect_database(path) as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return path
