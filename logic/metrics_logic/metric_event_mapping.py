from database.quality_model_loader import scan_quality_model_folder
from config.settings import QUALITY_MODELS_DIR

def load_required_fields_metrics(filepath: str)-> dict:
    """
    Reads some keys from the .properties metrics files. Returns a dict with those fields
    """
    allowed_keys = {'name', 'relatedEvent', 'scope', 'metric','description','factors','weights','enabled'}
    props = {}
    params = {}
    
    # Opeen the properties file and read the lines
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            # Collect the properties that we are interested in
            if key in allowed_keys:
                props[key] = value
            # Collect the parameters that we are interested in
            elif key.startswith('param.'):
                raw = value.strip() #Get the value of the parameter
                try:                     # turn to int/float if we can
                    val = int(raw) if raw.isdigit() else float(raw)
                except ValueError: #if not a number, keep it as string
                    val = raw
   
                params[key[6:]] = val
        # Attach any params to the props dict     
        if params:
            props['params'] = params
                
    return props


def build_metric_def(props: dict, qm: str, path: str) -> dict:
    '''
    Builds a metric definition from the loaded properties file.
    '''
    return {
        "filePath": path,
        "name": props["name"],
        "scope": props.get("scope", "team"),
        "formula": props["metric"],
        "params": props.get("params", {}),
        "description": props.get("description", ""),
        "factors": [x.strip() for x in props.get("factors","").split(",") if x],
        "weights": [float(w) for w in props.get("weights","").split(",") if w],
        "quality_model": qm,
    }

def build_metrics_index_per_qm(qm_root=QUALITY_MODELS_DIR)-> dict:
    '''
    Scans the quality model folder and builds a dictionary with the metrics found in each quality model.
    '''
    return scan_quality_model_folder(
        qm_root,
        subfolder="metrics",
        props_loader=load_required_fields_metrics,
        build_def=build_metric_def
    )
    

