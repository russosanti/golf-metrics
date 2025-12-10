from pathlib import Path
import pandas as pd
import streamlit as st
import re

DATA_DIR = Path("data")
SESSIONS_DIR = DATA_DIR / "sessions"


def ensure_dirs() -> None:
    """
    Crea las carpetas necesarias si no existen.
    """
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_sessions(files) -> list[Path]:
    """
    Guarda los archivos subidos por el usuario en data/sessions.
    Devuelve la lista de rutas guardadas.
    """
    ensure_dirs()
    saved_paths: list[Path] = []

    for f in files:
        # limpiamos un poco el nombre (solo letras, números, _ - .)
        safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", f.name)
        target_path = SESSIONS_DIR / safe_name

        with target_path.open("wb") as out:
            out.write(f.read())

        saved_paths.append(target_path)

    return saved_paths


def parse_session_label(filename: str) -> str:
    """
    Convierte algo tipo 'saturday__05_46_pm.csv'
    en 'Saturday 05:46 PM'.

    Si el nombre no sigue ese patrón, devuelve el nombre sin extensión.
    """
    name = Path(filename).stem  # sin extensión
    parts = name.split("__")

    if len(parts) == 2:
        day_part, time_part = parts
        day_part = day_part.capitalize()
        time_part = time_part.replace("_", ":").upper()
        return f"{day_part} {time_part}"

    return name


def load_all_sessions() -> pd.DataFrame:
    """
    Lee todos los CSV de data/sessions y los concatena.
    Agrega columnas:
      - SessionFile  (nombre del archivo)
      - SessionLabel (label legible)
    Normaliza la columna 'club' como string.
    """
    ensure_dirs()
    files = sorted(SESSIONS_DIR.glob("*.csv"))
    dfs: list[pd.DataFrame] = []

    for f in files:
        try:
            df = pd.read_csv(f)
        except Exception:
            # por si el CSV viene con otro separador
            df = pd.read_csv(f, sep=";")

        df["SessionFile"] = f.name
        df["SessionLabel"] = parse_session_label(f.name)

        if "club" not in df.columns:
            st.error(f"El archivo {f.name} no tiene columna 'club'. Se omite.")
            continue

        df["club"] = df["club"].astype(str)
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)