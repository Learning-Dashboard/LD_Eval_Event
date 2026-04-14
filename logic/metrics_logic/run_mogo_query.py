from logic.metrics_logic.metric_placeholder import load_query_template, replace_placeholders_in_query
from config.load_config_file import get_event_meta
from config.logger_config import setup_logging
from database.mongo_client import get_collection

import logging
setup_logging()
logger = logging.getLogger(__name__)




def evaluate_formula(formula_str: str, result_doc: dict) -> float: 
    """
    Evaluate the formula string using the values from the result_doc.
    """
    # create a variable dict with all keys from the doc
    # e.g. commitsAssignee -> 10, commitsTotal -> 11
    local_vars = {}
    
    #Scan the result_doc and create a dictionary with the values of the keys
    for k, v in result_doc.items(): 
        if isinstance(v, (int, float)): # if the value is a number, we can use it directly
            local_vars[k] = float(v) # convert to float for safety
        else: # if the value is not a number, we can skip it or set it to 0.0
            local_vars[k] = 0.0  
            
            
    # Now evaluate the expression
    try:
        ## Use eval to evaluate the formula string with the local_vars as context
        value = eval(formula_str, {}, local_vars) #eval takes a string expression and "transforms" it into a python expression that can be calculated
    except ZeroDivisionError: # handle division by zero
        value = 0.0
    except Exception as e: # handle any other exceptions giving the error and set to 0
        print(f"[evaluate_formula] Error: {e}, defaulting to 0.0")
        value = 0.0
    return value







def run_mongo_query_for_metric(team_name: str, student_name: str, query_file: str, event_type, placeholder_map: dict) -> dict:
    """
    Run a MongoDB query for a specific metric and return the result.
    """
    
    # #possible related_events sent by LD_connect from GITHUB: push, issues       from TAIGA: issue, epic, task, userstory, relatedusertory

    meta = get_event_meta(event_type)
    logger.debug(f"Event meta: {meta}") #CHANGE THIS LATER TO DEBUG LEVEL


    if meta is None:
        logger.warning(f"Event type '{event_type}' not found in meta data.")
        return
    
    collection_name= f"{meta['data_source'].lower()}_{team_name}.{meta['collection_suffix']}"  
    

    # load the aggregator pipeline from the .query file    
    pipeline = load_query_template(query_file, placeholder_map) #load the query template from the file and replace the placeholders with the values in the param_map
    logger.debug(f"pipeline: {pipeline}") #REMOVED LATER, ONLY TO LOG
    
    
    # .query has placeholders  "$$studentUser", need the function to recursively replace them
    pipeline = replace_placeholders_in_query(pipeline, {"$$studentUser": student_name})
    

    # connect to mongo, run the pipeline
    
    collection = get_collection(collection_name) #get the collection from the mongo client
    cursor = collection.aggregate(pipeline)
    results = list(cursor)
    logger.info(f"Results: {results}") #REMOVED LATER, ONLY TO LOG

    if not results: #if for some case the query returns no results, we return 0,0 
        return {} 

    doc = results[0]
    
    return doc
