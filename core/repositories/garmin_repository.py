from pathlib import Path
import pandas as pd
import re

DATA_DIR = Path("data")
GARMIN_DIR = DATA_DIR / "garmin_rounds"
GARMIN_DIR.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def save_round_dataframe(
    df: pd.DataFrame,
    round_id: str,
    date_str: str,
    course_name: str | None = None,
) -> Path:
    """
    Guarda una ronda normalizada como CSV en data/garmin_rounds.
    """
    GARMIN_DIR.mkdir(parents=True, exist_ok=True)

    if course_name:
        course_slug = slugify(course_name)
        filename = f"{date_str}_{course_slug}_{round_id}.csv"
    else:
        filename = f"{date_str}_{round_id}.csv"

    path = GARMIN_DIR / filename
    df.to_csv(path, index=False)
    return path


def load_all_rounds() -> pd.DataFrame:
    """
    Lee todos los CSV de data/garmin_rounds y los concatena.
    """
    GARMIN_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(GARMIN_DIR.glob("*.csv"))

    dfs: list[pd.DataFrame] = []

    for f in files:
        df = pd.read_csv(f)
        df["RoundFile"] = f.name
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)