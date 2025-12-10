import streamlit as st
import plotly.express as px

from core.repositories.mevo_repository import (
    ensure_dirs,
    save_uploaded_sessions,
    load_all_sessions,
)
from core.services.metrics_service import (
    METRIC_CANDIDATES,
    club_sort_key,
    build_smash_agg,
    build_smash_trend,
)
from core.repositories.garmin_repository import load_all_rounds
from core.services.garmin_service import sync_latest_garmin_rounds

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

Además: integración (en progreso) con **Garmin Golf** para tus rondas en cancha.
"""
)

# Aseguramos que los directorios existen
ensure_dirs()

# ---------------------------
# SIDEBAR: IMPORT MEVO + GARMIN
# ---------------------------

st.sidebar.header("⚙️ Control")

# --- MEVO ---
st.sidebar.subheader("Importar sesiones Mevo")

new_files = st.sidebar.file_uploader(
    "Subí uno o más CSV exportados del Mevo+",
    type=["csv"],
    accept_multiple_files=True,
)

if new_files:
    save_uploaded_sessions(new_files)
    st.sidebar.success(f"Se importaron {len(new_files)} archivo(s) de Mevo.")
    st.rerun()

# --- GARMIN ---
with st.sidebar.expander("⛳ Garmin Golf (beta)", expanded=False):
    email = st.text_input("Email Garmin", key="garmin_email")
    password = st.text_input("Password Garmin", type="password", key="garmin_pass")
    limit = st.number_input("Máx. rondas a sincronizar", min_value=1, max_value=50, value=10, step=1)

    if st.button("Sincronizar rondas Garmin"):
        if not email or not password:
            st.warning("Ingresá email y password de Garmin.")
        else:
            try:
                saved = sync_latest_garmin_rounds(email, password, limit=int(limit))
                st.success(f"Se sincronizaron {len(saved)} rondas (si Garmin devolvió scorecards).")
                st.rerun()
            except Exception as e:
                st.error(f"Error al sincronizar con Garmin: {e}")

# ---------------------------
# CARGA DE DATOS MEVO
# ---------------------------

data = load_all_sessions()

if data.empty:
    st.info("No hay sesiones Mevo guardadas todavía. Importá al menos un CSV en la barra lateral.")
    st.stop()

# ---------------------------
# DEFINICIÓN DE MÉTRICAS Y PALOS
# ---------------------------

metric_options = [c for c in METRIC_CANDIDATES if c in data.columns]
all_clubs = sorted(data["club"].unique(), key=club_sort_key)

# ---------------------------
# FILTROS EN SIDEBAR (MEVO)
# ---------------------------

st.sidebar.subheader("Filtros Mevo")

session_labels = (
    data[["SessionFile", "SessionLabel"]]
    .drop_duplicates()
    .sort_values("SessionLabel")
)

selected_sessions = st.sidebar.multiselect(
    "Sesiones",
    options=session_labels["SessionFile"],
    format_func=lambda x: session_labels.loc[
        session_labels["SessionFile"] == x, "SessionLabel"
    ].iloc[0],
    default=session_labels["SessionFile"].tolist(),
)

selected_clubs = st.sidebar.multiselect(
    "Palos",
    options=all_clubs,
    default=all_clubs,
)

default_metric_index = (
    metric_options.index("Carry (yds)")
    if "Carry (yds)" in metric_options
    else 0
)

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
    st.warning("No hay datos Mevo para los filtros seleccionados.")
    st.stop()

# ---------------------------
# TABS
# ---------------------------

tab_resumen, tab_graficos, tab_dispersion, tab_datos, tab_garmin = st.tabs(
    ["📌 Resumen Mevo", "📈 Gráficos Mevo", "🎯 Dispersión Mevo", "📋 Datos Mevo", "⛳ Rondas Garmin"]
)

# ---------------------------
# TAB 1: RESUMEN / INDICADORES (MEVO)
# ---------------------------
with tab_resumen:
    st.subheader("📌 Indicadores inteligentes por palo y sesión (Mevo)")

    base_metric = "Carry (yds)" if "Carry (yds)" in filtered.columns else "Smash"
    smash_agg = build_smash_agg(filtered, base_metric=base_metric)

    if smash_agg.empty:
        st.info("No se encontró la columna 'Smash' para calcular indicadores.")
    else:
        trend_df = build_smash_trend(smash_agg)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Eficiencia y consistencia por palo/sesión")
            st.dataframe(
                smash_agg[
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

# ---------------------------
# TAB 2: GRÁFICOS (MEVO)
# ---------------------------
with tab_graficos:
    st.subheader(f"📈 {selected_metric} por sesión y palo (Mevo)")

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

    st.subheader("📊 Promedios por sesión y palo (Mevo)")

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
# TAB 3: DISPERSIÓN (MEVO)
# ---------------------------
with tab_dispersion:
    st.subheader("🎯 Dispersión de los tiros (Curve Dist vs Carry, Mevo)")

    if "Curve Dist (yds)" in filtered.columns and "Carry (yds)" in filtered.columns:
        scat = filtered.dropna(subset=["Curve Dist (yds)", "Carry (yds)"]).copy()
        scat["shot_label"] = (
            "Sesión: " + scat["SessionLabel"].astype(str)
            + "<br>Palo: " + scat["club"].astype(str)
            + (
                "<br>Shot: " + scat["Shot"].astype(str)
                if "Shot" in scat.columns
                else ""
            )
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
        fig_scatter.add_vline(x=0, line_dash="dot")
        fig_scatter.add_hline(y=0, line_dash="dot")

        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("No se encontraron columnas 'Curve Dist (yds)' y 'Carry (yds)' para el gráfico de dispersión.")

# ---------------------------
# TAB 4: DATOS CRUDOS (MEVO)
# ---------------------------
with tab_datos:
    st.subheader("📋 Datos crudos Mevo filtrados")

    cols_to_show = ["SessionLabel", "club"]
    if "Shot" in filtered.columns:
        cols_to_show.append("Shot")
    cols_to_show += metric_options
    cols_to_show = [c for c in cols_to_show if c in filtered.columns]

    st.dataframe(filtered[cols_to_show].round(3))

# ---------------------------
# TAB 5: RONDAS GARMIN (MUY BÁSICO DE MOMENTO)
# ---------------------------
with tab_garmin:
    st.subheader("⛳ Rondas Garmin (beta)")

    garmin_df = load_all_rounds()
    if garmin_df.empty:
        st.info("Todavía no hay rondas Garmin sincronizadas o parseadas correctamente.")
    else:
        # Resumen muy básico por ronda
        if {"round_id", "date", "course_name", "score", "par"}.issubset(garmin_df.columns):
            summary = (
                garmin_df.groupby(["round_id", "date", "course_name"])
                .agg(
                    total_score=("score", "sum"),
                    total_par=("par", "sum"),
                    holes=("hole", "count"),
                    putts=("putts", "sum"),
                )
                .reset_index()
            )
            summary["vs_par"] = summary["total_score"] - summary["total_par"]

            st.markdown("### Resumen de rondas")
            st.dataframe(summary)

        st.markdown("### Datos crudos de hoyos (Garmin)")
        st.dataframe(garmin_df.head(200))