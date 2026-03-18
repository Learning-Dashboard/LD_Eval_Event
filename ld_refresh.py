import os
import logging
import requests
import time
from API_calls.StudentDatafromLDRESTAPI import build_team_students_map
from config.quality_model_config import load_qualitymodel_map, choose_qualitymodel
from config.load_config_file import get_available_events
from database.mongo_client import db

API_URL = os.getenv("EVAL_API_URL", "http://localhost:5001/api/event")

QM_MAP = load_qualitymodel_map()

EVENT_TYPES = ["push", "task", "userstory"]


def team_is_active(team_id: str) -> bool:
    """Function to check if a team has any activity in the database.
    If not active, it will not trigger any events."""
    coll = f"metrics.{team_id}"  # We will only check the metrics collection, because if it has metrics, the factors and indicators collections will also have data.
    return (
        coll in db.list_collection_names() and db[coll].estimated_document_count() > 0
    )


def trigger_team_event(team_id: str, event_type: str) -> None:
    """Function to trigger an event for a team.
    It will send a POST request to the API with the event data."""
    payload = {
        "event_type": event_type,
        "prj": team_id,
        "author_login": "system",
        "quality_model": choose_qualitymodel(team_id, None, QM_MAP),
    }
    start = time.perf_counter()
    r = requests.post(
        API_URL, json=payload, timeout=(0.2, 1)
    )  # connect timeout 0.2s, read timeout 1s


def delete_orphan_collections_from_mongo(actual_teams):
    for prefix in [
        "metrics",
        "factors",
        "strategic_indicators",
    ]:  # afegeix tots els prefixes que toquin
        collections = db.list_collection_names()
        for coll in collections:
            if coll.startswith(prefix + "."):
                team_collection = coll.split(".", 1)[1]
                if team_collection not in actual_teams:
                    db.drop_collection(coll)


def delete_orphan_student_documents(team_students_map):
    """
    Elimina documentos de estudiantes que ya no existen en el mapa de estudiantes.
    Busca en las colecciones metrics, factors y strategic_indicators.
    """
    for team_id, sources in team_students_map.items():
        # Obtener lista de estudiantes válidos: incluye nombres reales (EXCEL) + usernames (GITHUB + TAIGA)
        valid_students = []
        valid_students.extend(sources.get("EXCEL", []))
        valid_students.extend(sources.get("GITHUB", []))
        valid_students.extend(sources.get("TAIGA", []))

        # Eliminar duplicados
        valid_students = list(set(valid_students))

        # Limpiar en cada tipo de colección
        for prefix in ["metrics", "factors", "strategic_indicators"]:
            collection_name = f"{prefix}.{team_id}"

            if collection_name not in db.list_collection_names():
                continue

            collection = db[collection_name]

            # Buscar documentos con student_name que no esté en la lista de válidos
            # Los documentos de equipo no tienen student_name, así que los ignoramos
            orphan_docs = collection.find(
                {"student_name": {"$exists": True, "$nin": valid_students}}
            )

            deleted_count = 0
            for doc in orphan_docs:
                student_name = doc.get("student_name")
                # Intentar obtener el nombre de la métrica/factor/indicador
                item_name = (
                    doc.get("metric_name")
                    or doc.get("factor_name")
                    or doc.get("indicator_name")
                    or doc.get("name", "documento")
                )

                collection.delete_one({"_id": doc["_id"]})
                deleted_count += 1


def run_daily_refresh() -> None:
    """Function to run the daily refresh of events."""
    TEAM_STUDENTS = build_team_students_map()
    actual_teams = list(TEAM_STUDENTS.keys())

    # 1. Eliminar colecciones de equipos que ya no existen
    delete_orphan_collections_from_mongo(actual_teams)

    # 2. Eliminar documentos de estudiantes que ya no están en los equipos
    # delete_orphan_student_documents(TEAM_STUDENTS)

    # 3. Recalcular métricas para todos los equipos activos
    for team in TEAM_STUDENTS.keys():  # Get all the teams from the TEAM_STUDENTS map
        """
        if not team_is_active(team):
            logging.info("Equipo %s sin actividad previa; se omite.", team) # If the team is not active, skip it
            continue
        """
        events = get_available_events()
        for event in events:  # If the team is active, trigger all the events
            trigger_team_event(team, event)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
    run_daily_refresh()
