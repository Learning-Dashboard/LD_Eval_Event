import os
from logic.metrics_logic.metric_placeholder import load_query_template, replace_placeholders_in_query
from logic.metrics_logic.store_metric_mongo import store_metric_result
from logic.metrics_logic.run_mogo_query import run_mongo_query_for_metric, evaluate_formula
from statistics import pstdev

from database.mongo_client import get_collection
from config.load_config_file import get_event_meta
from config.logger_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)



def compute_metric_for_student(metric_def: dict, event_type: str, student_name: str, team_name: str)-> None:
    """
    Compute, evaluate and store an individual metric for a given student.
    """
     # Derive the .query filename from the .properties path
    basepath = os.path.splitext(metric_def["filePath"])[0]  # strip ".properties" #HERE WE WILL PUT IT IN .ENV LATER
    query_file = basepath + ".query"
    
    meta = get_event_meta(event_type)
    collection_name= f"{meta['data_source'].lower()}_{team_name}.{meta['collection_suffix']}" 

    formula_str = metric_def["formula"]  # e.g. "commitsAssignee / commitsTotal"
    logger.info(f"Recomputing INDIV metric '{metric_def['name']}' formula=({formula_str}) for student='{student_name}' team with external_id='{team_name}'")
    
    # Prepare the placeholders, will replace $$studentUser with the student name
    param_map = { "$$studentUser": student_name }
    # Can be the case that we have parameters in the query, like the threshold for the stdev. If in the metric definition, we will replace them with the values in the query
    for pname, pval in metric_def.get("params", {}).items():
        param_map[f"{{{{{pname}}}}}"] = pval
    logger.debug(f"param_map: {param_map}")

    # Run the aggregation pipeline and get raw doc
    doc = run_mongo_query_for_metric(team_name, student_name, query_file, event_type, param_map)
    logger.debug(f"doc: {doc}")
    
    
    if not doc:
        final_val=0.0
        logger.warning(f"No aggregator results, setting final_val to 0.0")
    else:
        # Evaluate the formula against the aggregation result
        final_val=evaluate_formula(formula_str,doc)
    logger.info(f"Result: {final_val}\n")
    
    # Store the metric result in MongoDB
    store_metric_result(team_name=team_name, metric_def=metric_def, final_val=final_val, event_type=event_type, student_name=student_name, aggregator_doc=doc, info_collection_name=collection_name)
    



def compute_metric_for_team(metric_def: dict, event_type: str, team_name: str,students: list)-> None:
    """
    Compute, evaluate and store a team-level metric (no individual placeholders).
    """
    # Obtasin the meta data for the event type. Will return the Source and collection suffix
    meta = get_event_meta(event_type)
    if meta is None:
        logger.warning(f"Unknown event type '{event_type}', skipping metric")
        return
    logger.debug(f"Event meta: {meta}")
    
    
    collection_name= f"{meta['data_source'].lower()}_{team_name}.{meta['collection_suffix']}"  
    print(f"Collection name: {collection_name}")
    collection = get_collection(collection_name)
    basepath = os.path.splitext(metric_def["filePath"])[0]
    query_file = basepath + ".query"
    formula_str = metric_def["formula"]
    
    # For standard deviation metrics, delegate to special handler
    if formula_str in ["stdevCommits", "stdevTasks"]:
        return compute_team_sd_metric(metric_def, event_type, team_name, collection_name, students)
    
    else:
        
        logger.info(f"Recomputing TEAM metric '{metric_def['name']}' formula=({formula_str}) for team with external_id='{team_name}'")
        
        # Load and substitute the placeholders in the query template
        param_map={} #Empty param map as we are not using any placeholders in any team query
        # Can be the case that we have parameters in the query, like the threshold for the stdev. If in the metric definition, we will replace them with the values in the query
        for pname, pval in metric_def.get("params", {}).items():
            param_map[f"{{{{{pname}}}}}"] = pval
        
        # Run the aggregation pipeline and get raw doc
        pipeline = load_query_template(query_file, param_map) #Load the query template, we will replace the placeholders later if needed
        pipeline = replace_placeholders_in_query(pipeline, param_map)

        

        results = list(collection.aggregate(pipeline))
        
        logger.debug(f"pipeline: {pipeline}") 
        logger.debug(f"db collection name: {collection_name}") 
        logger.debug(f"Results from aggregator: {results}")



        if not results:
            final_val = 0.0
            logger.warning(f"No aggregator results; defaulting to {final_val}")
            doc = {} # If no results, we can set doc to empty dict or None
        else:
            # Evaluate the formula
            doc = results[0]   # aggregator typically returns one doc
            final_val = evaluate_formula(formula_str, doc)

        logger.info(f"TEAM metric result: {final_val}\n")
        # Store the metric result in MongoDB
        store_metric_result( team_name=team_name, metric_def=metric_def, final_val=final_val, event_type=event_type, student_name=None, aggregator_doc=doc, info_collection_name=collection_name)
    


def compute_team_sd_metric(metric_def, event_type, team_name, collection_name, team_members=None):
    """
    Special-case: compute population standard deviation of counts per member.
    """
    
    basepath = os.path.splitext(metric_def["filePath"])[0]
    query_file = basepath + ".query"
    logger.info(f"Recomputing metric '{metric_def['name']}' for team with external_id='{team_name}'")

    collection= get_collection(collection_name)

    # Load and substitute the placeholders in the query template
    param_map={} #Empty param map as we are not using any placeholders in any team query
        # Can be the case that we have parameters in the query, like the threshold for the stdev. If in the metric definition, we will replace them with the values in the query
    for pname, pval in metric_def.get("params", {}).items():
        param_map[f"{{{{{pname}}}}}"] = pval
    
    #Load the query template
    pipeline = load_query_template(query_file, param_map) 

    docs = list(collection.aggregate(pipeline))
    logger.debug(f"Aggregator results: {docs}")

    # Build the aggregator map from the results
    aggregator_map = {}
    for d in docs:
        user = d["_id"]
        aggregator_map[user] = d["count"]

    print(f"Aggregator map: {aggregator_map}")
    # If we have no team_members, set an empty list
    if not team_members:
        team_members = []

    # Create a list of team members with 0 if not in the map
    commitsTotal=sum(aggregator_map.values()) # total number of commits/tasks
    
    if commitsTotal == 0:
        final_val = 0.0
        logger.warning("No commits in team, setting stdev to 0.0")
        aggregator_doc = {
            "perUserCounts": aggregator_map,
            "teamMembers": team_members
        }
        store_metric_result(
            team_name=team_name,
            metric_def=metric_def,
            final_val=final_val,
            event_type=event_type,
            student_name=None,
            aggregator_doc=aggregator_doc,
            info_collection_name=collection_name
        )
        logger.info(f"Final stdev: {final_val}\n")
        return final_val
    
    
    
    fractions = [
    aggregator_map.get(member, 0) / commitsTotal for member in team_members
]

    # Calculate the standard deviation of the fractions
    if len(fractions) > 1:
        final_val = pstdev(fractions)
    else:
        final_val = 0.0

    # Create the aggregator document to store in MongoDB
    aggregator_doc = {
        "perUserCounts": aggregator_map,
        "teamMembers": team_members
    }

    # Store the metric result in MongoDB
    store_metric_result(team_name=team_name, metric_def=metric_def, final_val=final_val, event_type=event_type, student_name=None, aggregator_doc=aggregator_doc, info_collection_name=collection_name)
    logger.info(f"Final stdev: {final_val}\n")
    return final_val





