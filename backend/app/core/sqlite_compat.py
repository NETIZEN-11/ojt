"""
SQLite compatibility shim for PostgreSQL-specific SQLAlchemy types.
Import this early (before any models) to replace JSONB, ARRAY, UUID.
"""
import os
import sys
import types

from sqlalchemy import JSON, String, Text
from sqlalchemy.types import TypeDecorator

DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_SQLITE = DATABASE_URL.startswith("sqlite")


class ArrayAsJSON(TypeDecorator):
    """Store arrays as JSON strings in SQLite."""
    impl = Text
    cache_ok = True

    def __init__(self, item_type=None, **kw):
        super().__init__(**kw)

    def process_bind_param(self, value, dialect):
        import json
        if value is None:
            return "[]"
        return json.dumps(list(value))

    def process_result_value(self, value, dialect):
        import json
        if value is None:
            return []
        return json.loads(value)


if IS_SQLITE:
    import sqlite3
    import uuid
    sqlite3.register_adapter(uuid.UUID, lambda u: str(u))
    pg_mod = types.ModuleType("sqlalchemy.dialects.postgresql")
    pg_mod.JSONB = JSON
    pg_mod.ARRAY = ArrayAsJSON
    pg_mod.UUID = String
    sys.modules["sqlalchemy.dialects.postgresql"] = pg_mod
