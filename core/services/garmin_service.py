# core/services/garmin_service.py

from typing import List
import pandas as pd
import json

from core.clients.garmin_client import GarminClient, GarminCredentials
from core.repositories.garmin_repository import save_round_dataframe
from core.utils.logger import get_logger

logger = get_logger("garmin_service")


def extract_round_holes(activity: dict) -> pd.DataFrame | None:
    logger.debug("Intentando extraer scorecard de una actividad...")

    scorecard = activity.get("golfScorecard") or activity.get("golfGame")

    if not scorecard:
        logger.warning("⚠️ No se encontró 'golfScorecard' ni 'golfGame'")
        return None

    holes = scorecard.get("holes") or scorecard.get("golfHoles") or []

    if not holes:
        logger.warning("⚠️ No se encontraron hoyos en el scorecard")
        return None

    rows: List[dict] = []

    for hole in holes:
        rows.append(
            {
                "hole": hole.get("holeNumber") or hole.get("hole"),
                "par": hole.get("par"),
                "score": hole.get("score"),
                "putts": hole.get("putts"),
                "fairway": hole.get("fairwayHit"),
                "green": hole.get("greenInRegulation") or hole.get("gir"),
                "drive_distance": hole.get("driveDistance") or hole.get("teeShotDistance"),
            }
        )

    df = pd.DataFrame(rows)
    logger.info(f"✅ Scorecard parseado: {len(df)} hoyos")
    return df


def sync_latest_garmin_rounds(email: str, password: str, limit: int = 10):
    logger.info("==== INICIANDO SINCRONIZACIÓN GARMIN ====")

    credentials = GarminCredentials(email=email, password=password)
    client = GarminClient(credentials)

    client.login()

    activities = client.fetch_golf_activities(limit=limit)

    if not activities:
        logger.warning("⚠️ No se encontraron actividades de golf")
        return []

    saved_files = []

    for idx, act in enumerate(activities):
        logger.info(f"Procesando ronda {idx + 1}/{len(activities)}")

        # DEBUG CRUDO (solo 1 vez)
        if idx == 0:
            with open("debug_garmin_activity.json", "w") as f:
                json.dump(act, f, indent=2)
            logger.info("📝 Se guardó 'debug_garmin_activity.json' para inspección")

        round_id = str(act.get("activityId") or act.get("activityIdLong") or "unknown")
        start_time = act.get("startTimeLocal") or act.get("startTimeGMT")
        course_name = act.get("locationName") or act.get("activityName")

        if isinstance(start_time, str):
            date_str = start_time[:10]
        else:
            date_str = "unknown"

        df = extract_round_holes(act)

        if df is None or df.empty:
            logger.warning(f"⚠️ Ronda {round_id} sin scorecard parseable")
            continue

        df["round_id"] = round_id
        df["date"] = date_str
        df["course_name"] = course_name

        path = save_round_dataframe(
            df,
            round_id=round_id,
            date_str=date_str,
            course_name=course_name,
        )

        logger.info(f"✅ Ronda guardada en: {path}")
        saved_files.append(path)

    logger.info(f"==== FIN SINCRONIZACIÓN GARMIN: {len(saved_files)} rondas guardadas ====")
    return saved_files