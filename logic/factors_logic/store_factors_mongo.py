from datetime import datetime
from zoneinfo import ZoneInfo
import os
import itertools

from database.mongo_client import get_collection


def store_factor_result(team_name:str, factor_def: dict, final_value: float, intermediate_metric_values: dict)-> None:
    '''
    Insert a indicator result into the MongoDB database under a certain collection name.
    '''
    # Sets the collection name to the team name + "_indicators"   
    collection = get_collection(f"factors.{team_name}")

    # Sets the evaluation date to the current date and time in the Europe/Madrid timezone
   #evaluation_date = datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d,%H:%M:%S")
    evaluation_date = datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d")

    # Factor label, its the name .properties file, for instance task_effort.properties metric, the name is task_effort
    full_path = factor_def["filePath"]
    factor_name = os.path.splitext(os.path.basename(full_path))[0]

    #Map the factor metric to a weight if it exists, otherwise use an empty list
    weight_map = dict(zip(
        factor_def.get("metric", []),
        factor_def.get("weights", [])
    ))

        # Build a unique _id: team-factorName-timestamp
    _id = f"{team_name}_{factor_name}_{evaluation_date}"
    
    # We need to check if the document already exists, and if it does, we increment the number of times modified
    # Check if the document already exists
    existing_doc = collection.find_one({"_id": _id})
    if existing_doc:
        # If it exists, increment the number of times modified
        n = existing_doc.get("times_modified", 0) + 1
    else:
        n=1

    metric_parts = []
    for metric_root, tuples in intermediate_metric_values.items():
        base_w = weight_map.get(metric_root, None)
        is_weighted = base_w not in (None, 1, 1.0)

        for student, val in tuples:
            
            if student is None:
                label = metric_root
            else:
                label = f"{metric_root}_{student}"

            weight_text = f"{str(base_w) if is_weighted else 'no weighted'}"
            
            metric_parts.append(
                f"{label} (value: {round(val, 10)}, {weight_text})"
            )
            

    metrics_block = "; ".join(metric_parts)+ ";"
    formula_name  = factor_def.get("formula", "average")
    category      = factor_def.get("category", "NoCategory")

    info_field = (
        f"metrics: {{ {metrics_block} }}, "
        f"formula: {formula_name}, "
        f"value: {round(final_value, 10)}, "
        f"category: {category}"
    )
    

    # Part of the mongo document that does not change
    static = {
        "name"         : factor_def['name'],
        "description"  : factor_def['description'],
        "project"      : team_name,
        "factor"       : factor_name,
        "indicators"   : factor_def.get("indicators", []),
        "datasource"   : "QRapids Dashboard",
        "missing_metrics": [],
        "dates_mismatch_days": 0,
        "createdAt"  : datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Part of the mongo document that will change each time there is an event
    dynamic = {
        "evaluationDate": evaluation_date,
        "value"        : final_value,
        "info"         : info_field,
        "modifiedAt"  : datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S"),
        "times_modified": n,
    }
    
 
        

    
     # Insert into MongoDB, with the dynamic and static parts, upserting or inserting
    collection.update_one(
        {"_id": _id},
        {
            "$set": dynamic,
            "$setOnInsert": static
            },
        upsert=True        
        )


