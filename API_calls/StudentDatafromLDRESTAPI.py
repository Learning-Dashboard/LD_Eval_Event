import requests
import time
import logging
from config.settings import BASE_GESSI_URL, LD_API_KEY, LD_API_KEY_HEADER

logger = logging.getLogger(__name__)

LD_HEADERS = {LD_API_KEY_HEADER: LD_API_KEY}

def fetch_projects() -> list:
    """
    Retrieve the list of projects from the LD REST API.
    """
    url = f"{BASE_GESSI_URL}/projects"
    
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=LD_HEADERS, timeout=60)
            response.raise_for_status()  # Raise an exception if status != 200
            projects = response.json()
            return projects
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to fetch projects from {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error(f"All {max_retries} attempts failed to fetch projects.")
                raise e
    return []


def fetch_project_details(project_id: int) -> dict:
    """
    Retrieve detailed information for a given project ID.
    """
    url = f"{BASE_GESSI_URL}/projects/{project_id}"
    # Use increased timeout here as well
    response = requests.get(url, headers=LD_HEADERS, timeout=60)
    response.raise_for_status()
    return response.json()


def build_team_students_map() -> dict:
    """
    Build a mapping from project external_id to student identity lists.
    """
    # Fetch all projects from the LD REST API
    projects = fetch_projects()
    team_students_map = {}

    # Loop through each project and fetch its details
    for proj in projects:
        p_id = proj["id"]
        ext_id = proj["externalId"]  # e.g. "AMEP11Beats"

        details = fetch_project_details(p_id)
        students_list = details.get("students") or []

        if not students_list:
            team_students_map[ext_id] = {}
            continue

        subdict = {}
        names_list = []

        # details["students"] is an array of student objects
        if not details["students"]:
            # no students => maybe skip or store empty
            team_students_map[ext_id] = {"GITHUB": [], "TAIGA": []}
            continue

        for student_obj in students_list:
            student_name = student_obj.get("name")
            if student_name:
                names_list.append(student_name)

            identities = student_obj.get("identities", {})
            # e.g. identities => {"GITHUB": {"username":"danipenalba"}, "TAIGA": {...}, "GITLAB": {...}}

            for data_source_name, identity_data in identities.items():
                # identity_data might be { "username": "someone123", ... }
                username = identity_data.get("username")
                if username:
                    # if we haven't used this data_source_name yet, create a list
                    if data_source_name not in subdict:
                        subdict[data_source_name] = []
                    subdict[data_source_name].append(username)

        subdict["EXCEL"] = names_list
        team_students_map[ext_id] = subdict

        # ADDED MANUALLY TO MAKE THE TESTS WORK, REMOVE LATER

    """
    team_students_map["LD_Test_Project"] = {
        "GITHUB": ["PabloGomezNa", "PepitoGomezNa", "charlie"],
        "TAIGA": ["pgomezn", "pablogz5", "Charlie55"],
        "EXCEL": ["Pablo", "Marc", "Charlie"]
    }
    """

    return team_students_map
