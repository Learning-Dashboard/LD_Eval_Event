from asyncio.log import logger
import os
import logging
import requests
import time
from API_calls.StudentDatafromLDRESTAPI import build_team_students_map
from config.quality_model_config import load_qualitymodel_map, choose_qualitymodel
from config.load_config_file import get_available_events, get_event_meta
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

    logger.info(
        f"Triggered event {event_type} for team {team_id} with status code {r.status_code} in {time.perf_counter() - start:.2f} seconds."
    )

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


def _valid_students_for_event(team_sources: dict, event_type: str) -> list:
    """
    Return valid student identifiers for a concrete event type.
    We must validate against the event data source only.
    """
    meta = get_event_meta(event_type)
    if not meta:
        return []

    data_source = meta.get("data_source")
    if not data_source:
        return []

    valid = team_sources.get(data_source, [])
    # Keep deterministic order while removing duplicates
    return list(dict.fromkeys(valid))


def _delete_invalid_students(collection, query: dict) -> int:
    """
    Delete documents that match the query.

    Prefer delete_many on real Mongo collections, but fall back to the
    test double API used in the unit tests.
    """
    if hasattr(collection, "delete_many"):
        result = collection.delete_many(query)
        return result.deleted_count

    deleted_count = 0

    docs = getattr(collection, "docs", None)
    if docs is None:
        for doc in collection.find(query):
            collection.delete_one({"_id": doc["_id"]})
            deleted_count += 1
        return deleted_count

    required_event_type = query.get("event_type")
    invalid_students = set(query["student_name"]["$nin"])

    for doc in list(docs):
        if "student_name" not in doc:
            continue
        if doc["student_name"] in invalid_students:
            continue
        if required_event_type is not None and doc.get("event_type") != required_event_type:
            continue

        collection.delete_one({"_id": doc["_id"]})
        deleted_count += 1

    return deleted_count

def delete_orphan_student_documents(team_students_map):
    """
    Elimina documentos de estudiantes que ya no existen en el mapa de estudiantes.
    Busca en las colecciones metrics, factors y strategic_indicators.
    La validación se hace por event_type y por su data source asociado,
    para evitar mezclar nombres EXCEL con usernames de TAIGA/GITHUB.
    """
    for team_id, sources in team_students_map.items():
        # Fallback list to protect legacy docs that may not have event_type.
        all_valid_students = list(dict.fromkeys(
            sources.get("EXCEL", []) + sources.get("GITHUB", []) + sources.get("TAIGA", [])
        ))

        try:
            collections = db.list_collection_names()
        except Exception as exc:
            logging.warning(
                "Skipping orphan student cleanup for %s because Mongo is unavailable: %s",
                team_id,
                exc,
            )
            return
        
        # Limpiar en cada tipo de colección
        for prefix in ["metrics", "factors", "strategic_indicators"]:
            collection_name = f"{prefix}.{team_id}"

            if collection_name not in collections:
                continue

            collection = db[collection_name]

            deleted_count = 0

            # 1) Remove docs with known event_type and invalid student for that source
            for event_type in get_available_events():
                valid_for_event = _valid_students_for_event(sources, event_type)
                if not valid_for_event:
                    continue

                deleted_count += _delete_invalid_students(collection, {
                    "student_name": {"$exists": True, "$nin": valid_for_event},
                    "event_type": event_type
                })

            # 2) Legacy docs without event_type: apply broad fallback validation
            deleted_count += _delete_invalid_students(collection, {
                "student_name": {"$exists": True, "$nin": all_valid_students},
                "event_type": {"$exists": False}
            })

            if deleted_count > 0:
                logging.info("Deleted %s orphan student documents from %s", deleted_count, collection_name)


def run_daily_refresh() -> None:
    """Function to run the daily refresh of events."""
    TEAM_STUDENTS = build_team_students_map()
    actual_teams = list(TEAM_STUDENTS.keys())

    # 1. Eliminar colecciones de equipos que ya no existen
    delete_orphan_collections_from_mongo(actual_teams)

    # 2. Eliminar documentos de estudiantes que ya no están en los equipos
    delete_orphan_student_documents(TEAM_STUDENTS)
    
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
