import os
from datetime import datetime
from zoneinfo import ZoneInfo
from database.mongo_client import get_collection


def store_indicator_result(team_name:str, indicator_def: dict, final_value: float, intermediate_factor_values: dict)-> None:
    '''
    Insert a indicator result into the MongoDB database under a certain collection name.
    '''
    # Sets the collection name to the team name + "_indicators"       
    collection= get_collection(f"strategic_indicators.{team_name}")

    # Sets the evaluation date to the current date and time in the Europe/Madrid timezone
    evaluation_date = datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d")

    # Indicator label, its the name .properties file, for instance task_effort.properties metric, the name is task_effort

    indicator_label = os.path.splitext(os.path.basename(indicator_def["filePath"]))[0]
    
    weight_map = dict(zip(
        indicator_def.get("factor", []),     # en tu .properties suele llamarse "factor"
        indicator_def.get("weights", [])
    ))
        
    _id = f"{team_name}_{indicator_label}_{evaluation_date}" 
        # We need to check if the document already exists, and if it does, we increment the number of times modified
    # Check if the document already exists
    existing_doc = collection.find_one({"_id": _id})
    if existing_doc:
        # If it exists, increment the number of times modified
        n = existing_doc.get("times_modified", 0) + 1
    else:
        n = 1
        
    # Build a unique _id: team-factorName-timestamp
    factor_parts = []
    for factor_name, tuples in intermediate_factor_values.items():
        base_w      = weight_map.get(factor_name, None)
        is_weighted = base_w not in (None, 1, 1.0)

        # The strategic indicator receives only 1 value always (student=None)
        # pero iteramos igual por coherencia
        for _student, val in tuples:
            wtxt = f"weighted:{base_w}" if is_weighted else "no weighted"
            factor_parts.append(
                f"{factor_name} (value: {round(val, 10)}, {wtxt})"
            )

    factors_block = "; ".join(factor_parts) + ";"
    formula_name  = indicator_def.get("formula", "average")
    category      = indicator_def.get("category", "Neutral")

    info_field = (
        f"factors: {{ {factors_block} }}, "
        f"formula: {formula_name}, "
        f"value: {round(final_value, 10)}, "
        f"category: {category}"
    )
    
        # Part of the mongo document that does not change
    static = {
        "name"         : indicator_def['name'],
        "description"  : indicator_def['description'],
        "project"      : team_name,
        "strategic_indicator"       : indicator_label,
        "datasource"  : "QRapids Dashboard",
        "dates_mismatch_days": 0,
        "missing_factors": [],
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
    
    

