# core/clients/garmin_client.py

from dataclasses import dataclass
from typing import List, Dict

import garth

from core.utils.logger import get_logger

logger = get_logger("garmin_client")


@dataclass
class GarminCredentials:
    email: str
    password: str


class GarminClient:
    def __init__(self, credentials: GarminCredentials) -> None:
        self.credentials = credentials

    def login(self) -> None:
        logger.info("Intentando login en Garmin...")
        garth.login(self.credentials.email, self.credentials.password)
        logger.info("✅ Login Garmin OK")

    def fetch_activities(self, limit: int = 50) -> List[Dict]:
        logger.info(f"Buscando actividades (limit={limit})...")

        resp = garth.connectapi(
            "/activitylist-service/activities/search/activities",
            params={"start": 0, "limit": limit},
        )

        if isinstance(resp, list):
            logger.info(f"✅ {len(resp)} actividades recibidas (lista directa)")
            return resp

        if isinstance(resp, dict) and "activities" in resp:
            activities = resp["activities"]
            logger.info(f"✅ {len(activities)} actividades recibidas (dict)")
            return activities

        logger.warning("⚠️ Respuesta inesperada de Garmin")
        logger.debug(resp)
        return []

    def fetch_golf_activities(self, limit: int = 50) -> List[Dict]:
        activities = self.fetch_activities(limit)
        logger.info("Filtrando solo actividades de golf...")

        golf_activities: List[Dict] = []

        for a in activities:
            type_key = (
                a.get("activityType", {}).get("typeKey")
                or a.get("activityType", {}).get("typeId")
            )

            if isinstance(type_key, str) and type_key.lower() == "golf":
                golf_activities.append(a)

        logger.info(f"✅ {len(golf_activities)} actividades de golf encontradas")
        return golf_activities