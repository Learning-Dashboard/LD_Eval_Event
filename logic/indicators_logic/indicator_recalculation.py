from logic.indicators_logic.store_indicator_mongo import store_indicator_result
from database.mongo_client import get_collection

def latest_factor_value(team, factor_name, student=None):
    '''
    Retrieve the latest factor value(s) from MongoDB for a given metric.
    '''
    

    # Sets the collection name to the team name + "_factors"
    coll = get_collection(f"factors.{team}")
    # Try finding any document for this factor
    doc = coll.find_one({'factor': factor_name})
        
    #if no document found, return empty list
    if doc is None: 
        return [(None, 0.0)]
    
    # if 'student_name' in doc: #means we have one individual value per student 
    #     pipeline = [
    #         {'$match': {'metric': factor_name}},
    #         {'$sort':  {'student_name': 1, 'evaluationDate': -1}},
    #         {'$group': {'_id': '$student_name',
    #                     'latest': {'$first': '$value'}}}
    #     ]
    #     return [(doc['_id'], doc['latest']) for doc in coll.aggregate(pipeline)]
    
    
    # If its a team metric, only one per team, we find it and return it as is
    doc = coll.find_one({'factor': factor_name}, sort=[('evaluationDate', -1)])
    
    return [(None, doc['value'])] if doc else []



def compute_indicator(team_name: str, indicator_def: dict, values_dict: dict)-> tuple:
    """
    Compute a factor's final value based on its constituent metric values.
    Supports 'average' and 'weighted_average' operations.
    """
    # Loop over the values_dict to get the values, the metric names and students
    flat_vals   = []
    flat_metric = []          # parallel list remembering which metric produced each val
    flat_student = []        # parallel list remembering which student produced each val
    
    # Loop over the values_dict to get the values, the metric names and students
    for m, tup_list in values_dict.items():
        for student, val in tup_list:
            flat_vals.append(val)           # List of all the values
            flat_metric.append(m)       # List of the names of the metrics that compose the factors
            flat_student.append(student) #List of the students names in case the factor uses an individual metric
    
    
    # No data return 0.0 and "no input"
    if not flat_vals:           
        return 0.0, "no input"

    # Get the operation to be performed from the indicator definition
    op = indicator_def.get('formula', 'average')

    # Calculate the final value based on the weighted average
    if op == 'average':
        final_val = sum(flat_vals)/len(flat_vals)
        info = f"avg({flat_vals})"

    # Calculate the final value based on the weighted average
    elif op == 'weighted_average':
        base_w = [float(w) for w in indicator_def.get('weights', [])]
        if not base_w or len(base_w) != len(indicator_def['metric']):
            base_w = [1.0]*len(indicator_def['metric'])
        # replicate each metric-weight for every student value
        metric2weight = dict(zip(indicator_def['metric'], base_w))
        w_expanded    = [metric2weight[m] for m in flat_metric]

        final_val  = sum(v*w for v, w in zip(flat_vals, w_expanded)) / sum(w_expanded)
        info = f"w_avg({list(zip(flat_metric, flat_vals, w_expanded))})"

    else:
        raise ValueError(f"Unknown operation '{op}'")

    #Store the factor result in the mongo database
    store_indicator_result(team_name=team_name, indicator_def=indicator_def, final_value=final_val,  intermediate_factor_values=values_dict)
    
    return final_val, info



