from pathlib import Path
import sqlite3

DB_PATH = Path("data") / "mevo.db"


def get_connection() -> sqlite3.Connection:
    """
    Devuelve una conexión a SQLite (data/mevo.db).
    No se usa aún, pero queda listo para el futuro.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)