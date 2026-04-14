import os 
from datetime import datetime
from zoneinfo import ZoneInfo
from database.mongo_client import get_collection
import re

#def store_metric_result(team_name: str, metric_name: str, scope: str, final_val: float, event_type: str, student_name: str = None, aggregator_doc: dict = None):
def store_metric_result(team_name: str, metric_def: str, final_val: float, event_type: str, student_name: str = None, aggregator_doc: dict = None, info_collection_name: str = None):
    '''
    Insert a metric result into the MongoDB database.
    '''
    collection_name = f"metrics.{team_name}"
    # Sets the collection name to the team name + "_metrics" 
    collection = get_collection(collection_name)
    # Sets the evaluation date to the current date and time in the Europe/Madrid timezone
    evaluation_date = datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d")
    
    # Metric label, its the name .properties file, for instance task_effort.properties metric, the name is task_effort
    full_path = metric_def["filePath"]
    filename = os.path.basename(full_path)
    metric_label = os.path.splitext(filename)[0]

    # Unique _id = project‑metric‑[student‑]date
    id_parts = [team_name, metric_label, evaluation_date]
    if student_name:
        id_parts.insert(2, student_name)           # add between team & date
    doc_id = "-".join(id_parts)

    # We need to check if the document already exists, and if it does, we increment the number of times modified
    # Check if the document already exists
    existing_doc = collection.find_one({"_id": doc_id})
    if existing_doc:
        # If it exists, increment the number of times modified
        n = existing_doc.get("times_modified", 0) + 1
    else:
        n=1

# just abans de construir info_lines:
    if student_name:
        query_props = { 'studentUser': student_name }
    else:
        query_props = {}

    
    # Compose the info block, with parameters and formula
    info_lines = [
        f"parameters: {{evaluationDate={evaluation_date}}}",
        f"query-properties: {query_props}",
    ]
    if aggregator_doc:
        info_lines.append(f"executionResults: {aggregator_doc}")
    info_lines.append(f"formula: {metric_def['formula']}")
    info_lines.append(f"value: {final_val}")
    info = "\n".join(info_lines)


    if student_name:
        
        username = re.sub(r"[ \-]", "_", student_name)
        
        static = {
            "name"         : f"{student_name} {metric_def['name']}",
            "description"  : metric_def['description'],
            "project"      : team_name,
            "metric"       : f"{metric_label}_{username}",
            "factors"      : metric_def.get("factors", []),
            "source"      : f"mongodb:27017/mongo.{info_collection_name}",
            "type"         : "metrics",
            "weights"      : metric_def.get("weights", []),
            "scope"        : "individual",
            "student_name" : student_name,
            "event_type"   : event_type,
            "createdAt"  : datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S"),
        }


        # Part of the mongo document that will change each time there is an event
        dynamic = {
            "evaluationDate": evaluation_date,
            "value"        : final_val,
            "info"         : info,
            "modifiedAt"  : datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S"),
            "times_modified": n,
        }
        


    else:
    # Part of the mongo document that does not change
        static = {
            "name"         : metric_def['name'],
            "description"  : metric_def['description'],
            "project"      : team_name,
            "metric"       : metric_label,
            "factors"      : metric_def.get("factors", []),
            "source"      : f"mongodb:27017/mongo.{info_collection_name}",
            "type"         : "metrics",
            "weights"      : metric_def.get("weights", []),
            "scope"        : "individual" if student_name else "team",
            "event_type"   : event_type,
            "createdAt"  : datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S"),
        }
        if student_name:    # If the metric is for a student, add the student name to the document
            static["student_name"] = student_name

        # Part of the mongo document that will change each time there is an event
        dynamic = {
            "evaluationDate": evaluation_date,
            "value"        : final_val,
            "info"         : info,
            "modifiedAt"  : datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S"),
            "times_modified": n,
        }
    
 
     # Insert into MongoDB, with the dynamic and static parts, upserting or inserting
    collection.update_one(
        {"_id": doc_id},
        {
            "$set": dynamic,
            "$setOnInsert": static
            },
        upsert=True        
        )
    
    
    