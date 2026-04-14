import json

def load_query_template(query_file, param_map=None) -> dict:
    """
    Loads the .query file as a Python object (list/dict).
    It also replaces the placeholders in the template with the values from the param_map.
    """
    with open(query_file, 'r', encoding='utf-8') as f:
        
        query_str = f.read()
    
    if param_map: 
        for placeholder, value in param_map.items(): #If we have a param_map, we replace the placeholders in the template with the values from the param_map, to avoid integer problems
            query_str = query_str.replace(placeholder, str(value))
    
    return json.loads(query_str)





def replace_placeholders_in_query(query_ast: list, param_map: dict) -> list:
    """
    All this function simply replaces the "$$StudentUser" for the value in param_map.
    In our case param_map will the name of the student in each state of the loop. 
    With that we can define once the query and use all the students names in the loop.
    
    If query_ast is a list, we need to iterate over each item and replace placeholders in each one.
    #Normally this is the case, the pipeline in mongo is a dictionary with the stages as keys and the values as the query.
    
    [
  { "$match": { "student": "$$studentUser" } },
  { "$group": { "_id": "$team", "count": { "$sum": 1 } } }
        ]
    """
    if isinstance(query_ast, dict):
        return {
            k: replace_placeholders_in_query(v, param_map)
            for k,v in query_ast.items()
        }
    #if the query_ast is a list, we need to iterate over each item and replace placeholders in each one.
    elif isinstance(query_ast, list):
        return [
            replace_placeholders_in_query(item, param_map)
            for item in query_ast
        ]
    # If query_ast is a string, we replace the placeholders with the real values from param_map.
    elif isinstance(query_ast, str):
        out_str = query_ast
        for placeholder, real_value in param_map.items():
            out_str = out_str.replace(placeholder, str(real_value))
        return out_str
    else:
        return query_ast