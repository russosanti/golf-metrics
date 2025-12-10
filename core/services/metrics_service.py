import numpy as np
import pandas as pd
import re


METRIC_CANDIDATES = [
    "Ball (mph)",
    "Club (mph)",
    "Smash",
    "Carry (yds)",
    "Total (yds)",
    "Roll (yds)",
    "Spin (rpm)",
    "Height (ft)",
    "Time (s)",
    "AOA (°)",
    "Spin Loft (°)",
    "Swing V (°)",
    "Curve Dist (yds)",
]


def calc_consistency(series: pd.Series) -> float:
    """
    Índice de consistencia entre 0 y 100.
    Más alto = más consistente (menor desviación relativa).
    """
    series = series.dropna()
    if len(series) < 3:
        return np.nan

    mean = series.mean()
    std = series.std()

    if mean == 0:
        return np.nan

    return max(0.0, 100.0 * (1.0 - std / mean))


def club_target_smash(club_name: str) -> float:
    """
    Smash factor ideal aproximado según tipo de palo.
    """
    name = club_name.lower()

    if "driver" in name:
        return 1.48
    if "wood" in name or "fw" in name or "3w" in name or "5w" in name:
        return 1.47
    if "hybrid" in name or "rescue" in name or "híbrido" in name:
        return 1.45
    if "wedge" in name or "gw" in name or "sw" in name or "lw" in name:
        return 1.25

    # Hierros por defecto
    return 1.33


def club_sort_key(c: str) -> int:
    """
    Orden lógico de palos:
    - Driver
    - Hierros (por número)
    - Wedges
    - Otros
    """
    name = c.lower()

    if "driver" in name:
        return 1

    match = re.search(r"(\d+)", name)
    if match:
        return 100 + int(match.group(1))  # hierro 4, 5, 6, etc.

    if "wedge" in name or "gw" in name or "sw" in name or "lw" in name:
        return 200

    return 300


def build_smash_agg(df: pd.DataFrame, base_metric: str = "Carry (yds)") -> pd.DataFrame:
    """
    Devuelve un dataframe agregado por:
      - SessionFile
      - SessionLabel
      - club

    Incluye:
      - shots
      - smash_avg
      - smash_std
      - target_smash
      - smash_diff
      - consistency_index   (en base a base_metric o Smash)
    """
    if "Smash" not in df.columns:
        return pd.DataFrame()

    agg = (
        df.groupby(["SessionFile", "SessionLabel", "club"])
        .agg(
            shots=("Shot", "count") if "Shot" in df.columns else ("Smash", "count"),
            smash_avg=("Smash", "mean"),
            smash_std=("Smash", "std"),
        )
        .reset_index()
    )

    agg["target_smash"] = agg["club"].apply(club_target_smash)
    agg["smash_diff"] = agg["smash_avg"] - agg["target_smash"]

    if base_metric not in df.columns:
        base_metric = "Smash"

    consistency_series = (
        df.groupby(["SessionFile", "SessionLabel", "club"])[base_metric]
        .apply(calc_consistency)
    )
    agg["consistency_index"] = consistency_series.values

    return agg


def build_smash_trend(agg: pd.DataFrame) -> pd.DataFrame:
    """
    A partir de la tabla agregada de smash (build_smash_agg),
    calcula la tendencia por palo:

    - Smash primera sesión
    - Smash última sesión
    - Diferencia
    - Tendencia (⬆️ / ⬇️ / ➡️)
    """
    if agg.empty:
        return pd.DataFrame()

    trend_rows: list[dict] = []

    for club in agg["club"].unique():
        club_data = agg[agg["club"] == club].sort_values("SessionLabel")
        if len(club_data) < 2:
            continue

        first = club_data.iloc[0]["smash_avg"]
        last = club_data.iloc[-1]["smash_avg"]
        diff = last - first

        if diff > 0.01:
            trend = "⬆️ Mejorando"
        elif diff < -0.01:
            trend = "⬇️ Empeorando"
        else:
            trend = "➡️ Estable"

        trend_rows.append(
            {
                "Palo": club,
                "Smash primera": round(first, 3),
                "Smash última": round(last, 3),
                "Δ Smash": round(diff, 3),
                "Tendencia": trend,
            }
        )

    return pd.DataFrame(trend_rows)