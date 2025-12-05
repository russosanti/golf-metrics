import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px
import re
import datetime as dt

# ---------------------------
# CONFIG GENERAL
# ---------------------------
st.set_page_config(
    page_title="Mevo+ Range Dashboard",
    layout="wide",
)

st.title("📊 Dashboard de práctica – FlightScope Mevo+")

st.markdown(
    """
Analizador de **sesiones de driving range** con tu Mevo+.

- Importás CSV desde la app
- Se guardan en una carpeta local (`data/sessions`)
- Podés filtrar por **sesión, palo y métrica**
- Ver:
  - Indicadores inteligentes
  - Progreso (línea)
  - Promedios (barras)
  - Dispersión de tiros
  - Datos crudos
"""
)

# Carpeta donde se guardan los CSV de sesiones
DATA_DIR = Path("data") / "sessions"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------
# HELPERS
# ---------------------------

def parse_session_label(filename: str) -> str:
    """
    Convierte algo tipo 'saturday__05_46_pm.csv'
    en un label más legible, p.ej. 'Saturday 05:46 PM'
    """
    name = Path(filename).stem  # sin extensión
    # Ejemplo esperado: 'saturday__05_46_pm'
    parts = name.split("__")
    if len(parts) == 2:
        day_part, time_part = parts
        day_part = day_part.capitalize()
        time_part = time_part.replace("_", ":").upper()
        return f"{day_part} {time_part}"
    else:
        return name  # fallback por si viene distinto


def load_all_sessions() -> pd.DataFrame:
    """
    Lee todos los CSV de DATA_DIR y los concatena.
    Agrega columna 'SessionFile' (nombre archivo) y 'SessionLabel'.
    """
    files = sorted(DATA_DIR.glob("*.csv"))
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
        except Exception:
            df = pd.read_csv(f, sep=";")

        df["SessionFile"] = f.name
        df["SessionLabel"] = parse_session_label(f.name)

        # normalizamos nombre de columna de palo
        if "club" not in df.columns:
            st.error(f"El archivo {f.name} no tiene columna 'club'.")
            continue
        df["club"] = df["club"].astype(str)

        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


def calc_consistency(series: pd.Series):
    series = series.dropna()
    if len(series) < 3:
        return np.nan
    mean = series.mean()
    std = series.std()
    if mean == 0:
        return np.nan
    # Índice entre 0 y 100 (más alto = más consistente)
    return max(0, 100 * (1 - std / mean))


def club_target_smash(club_name: str):
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


# ---------------------------
# SIDEBAR: IMPORT Y FILTROS
# ---------------------------

st.sidebar.header("⚙️ Control")

# Importar nuevas sesiones (se guardan en DATA_DIR)
st.sidebar.subheader("Importar nuevas sesiones")

new_files = st.sidebar.file_uploader(
    "Subí uno o más CSV exportados del Mevo+",
    type=["csv"],
    accept_multiple_files=True,
)

if new_files:
    for f in new_files:
        # limpiamos un poco el nombre
        safe_name = re.sub(r"[^a-zA-Z0-9_\-.]", "_", f.name)
        target_path = DATA_DIR / safe_name
        # guardamos el archivo
        with target_path.open("wb") as out:
            out.write(f.read())
    st.sidebar.success(f"Se importaron {len(new_files)} archivo(s).")
    # recargamos la app para que se vean las nuevas sesiones
    st.rerun()

# Cargamos todas las sesiones guardadas
data = load_all_sessions()

if data.empty:
    st.info("No hay sesiones guardadas todavía. Importá al menos un CSV en la barra lateral.")
    st.stop()

# Métricas interesantes
metric_candidates = [
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

metric_options = [c for c in metric_candidates if c in data.columns]

# Orden lógico de palos (muy básico, se puede mejorar)
def club_sort_key(c):
    # intenta detectar número
    match = re.search(r"(\d+)", c)
    if "driver" in c.lower():
        return 1
    if match:
        return 100 + int(match.group(1))  # hierro 4,5,6...
    if "wedge" in c.lower() or "gw" in c.lower() or "sw" in c.lower() or "lw" in c.lower():
        return 200
    return 300

all_clubs = sorted(data["club"].unique(), key=club_sort_key)

# Filtros en sidebar
st.sidebar.subheader("Filtros")

session_labels = (
    data[["SessionFile", "SessionLabel"]]
    .drop_duplicates()
    .sort_values("SessionLabel")
)

selected_sessions = st.sidebar.multiselect(
    "Sesiones",
    options=session_labels["SessionFile"],
    format_func=lambda x: session_labels.loc[session_labels["SessionFile"] == x, "SessionLabel"].iloc[0],
    default=session_labels["SessionFile"].tolist(),
)

selected_clubs = st.sidebar.multiselect(
    "Palos",
    options=all_clubs,
    default=all_clubs,
)

default_metric_index = metric_options.index("Carry (yds)") if "Carry (yds)" in metric_options else 0
selected_metric = st.sidebar.selectbox(
    "Métrica principal",
    metric_options,
    index=default_metric_index,
)

# Aplicar filtros
filtered = data[
    data["SessionFile"].isin(selected_sessions) & data["club"].isin(selected_clubs)
].copy()

if filtered.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

# ---------------------------
# TABS
# ---------------------------
tab_resumen, tab_graficos, tab_dispersion, tab_datos = st.tabs(
    ["📌 Resumen", "📈 Gráficos", "🎯 Dispersión", "📋 Datos crudos"]
)

# ---------------------------
# TAB 1: RESUMEN / INDICADORES
# ---------------------------
with tab_resumen:
    st.subheader("📌 Indicadores inteligentes por palo y sesión")

    if "Smash" in filtered.columns:
        # Agregamos
        agg = (
            filtered.groupby(["SessionFile", "SessionLabel", "club"])
            .agg(
                shots=("Shot", "count") if "Shot" in filtered.columns else ("Smash", "count"),
                smash_avg=("Smash", "mean"),
                smash_std=("Smash", "std"),
            )
            .reset_index()
        )

        agg["target_smash"] = agg["club"].apply(club_target_smash)
        agg["smash_diff"] = agg["smash_avg"] - agg["target_smash"]

        base_metric = "Carry (yds)" if "Carry (yds)" in filtered.columns else "Smash"
        consistency_series = (
            filtered.groupby(["SessionFile", "SessionLabel", "club"])[base_metric]
            .apply(calc_consistency)
        )
        agg["consistency_index"] = consistency_series.values

        # Tendencia (simple): primera vs última sesión por palo
        trend_rows = []
        for club in agg["club"].unique():
            club_data = (
                agg[agg["club"] == club]
                .sort_values("SessionLabel")  # simple orden alfabético
            )
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
        trend_df = pd.DataFrame(trend_rows)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Eficiencia y consistencia por palo/sesión")
            st.dataframe(
                agg[
                    [
                        "SessionLabel",
                        "club",
                        "shots",
                        "smash_avg",
                        "target_smash",
                        "smash_diff",
                        "consistency_index",
                    ]
                ]
                .round(3)
                .rename(
                    columns={
                        "SessionLabel": "Sesión",
                        "club": "Palo",
                        "shots": "Tiros",
                        "smash_avg": "Smash prom.",
                        "target_smash": "Smash ideal",
                        "smash_diff": "Δ Smash",
                        "consistency_index": "Índice consistencia (0-100)",
                    }
                )
            )

        with col2:
            st.markdown("#### Tendencia de Smash por palo (primera vs última sesión)")
            if not trend_df.empty:
                st.dataframe(trend_df)
            else:
                st.info("Se necesita más de una sesión por palo para calcular tendencia.")
    else:
        st.info("No se encontró la columna 'Smash' para calcular indicadores de eficiencia.")

# ---------------------------
# TAB 2: GRÁFICOS (LÍNEA + BARRAS)
# ---------------------------
with tab_graficos:
    st.subheader(f"📈 {selected_metric} por sesión y palo")

    line_agg = (
        filtered.groupby(["SessionFile", "SessionLabel", "club"])[selected_metric]
        .mean()
        .reset_index()
        .rename(columns={selected_metric: "value"})
    )

    fig_line = px.line(
        line_agg,
        x="SessionLabel",
        y="value",
        color="club",
        markers=True,
        labels={
            "SessionLabel": "Sesión",
            "value": selected_metric,
            "club": "Palo",
        },
    )
    fig_line.update_layout(legend_title_text="Palo")
    st.plotly_chart(fig_line, use_container_width=True)

    st.subheader("📊 Promedios por sesión y palo")

    fig_bar = px.bar(
        line_agg,
        x="SessionLabel",
        y="value",
        color="club",
        barmode="group",
        labels={
            "SessionLabel": "Sesión",
            "value": selected_metric,
            "club": "Palo",
        },
    )
    fig_bar.update_layout(legend_title_text="Palo")
    st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------
# TAB 3: DISPERSIÓN
# ---------------------------
with tab_dispersion:
    st.subheader("🎯 Dispersión de los tiros (Curve Dist vs Carry)")

    if "Curve Dist (yds)" in filtered.columns and "Carry (yds)" in filtered.columns:
        scat = filtered.dropna(subset=["Curve Dist (yds)", "Carry (yds)"]).copy()
        scat["shot_label"] = (
            "Sesión: " + scat["SessionLabel"].astype(str)
            + "<br>Palo: " + scat["club"].astype(str)
            + (("<br>Shot: " + scat["Shot"].astype(str)) if "Shot" in scat.columns else "")
        )

        fig_scatter = px.scatter(
            scat,
            x="Curve Dist (yds)",
            y="Carry (yds)",
            color="club",
            hover_name="shot_label",
            labels={
                "Curve Dist (yds)": "Distancia lateral (yds) (- = izquierda, + = derecha)",
                "Carry (yds)": "Carry (yds)",
                "club": "Palo",
            },
        )
        # líneas de referencia
        fig_scatter.add_vline(x=0, line_dash="dot")
        fig_scatter.add_hline(y=0, line_dash="dot")

        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("No se encontraron columnas 'Curve Dist (yds)' y 'Carry (yds)' para el gráfico de dispersión.")

# ---------------------------
# TAB 4: DATOS CRUDOS
# ---------------------------
with tab_datos:
    st.subheader("📋 Datos crudos filtrados")

    cols_to_show = ["SessionLabel", "club"]
    if "Shot" in filtered.columns:
        cols_to_show.append("Shot")
    cols_to_show += metric_options
    cols_to_show = [c for c in cols_to_show if c in filtered.columns]

    st.dataframe(filtered[cols_to_show].round(3))