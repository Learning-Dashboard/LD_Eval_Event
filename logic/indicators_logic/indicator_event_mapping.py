from database.quality_model_loader import scan_quality_model_folder
from config.settings import QUALITY_MODELS_DIR


def load_required_fields_indicator(filepath: str) -> dict:
    """
    Reads some allowed keys from the .properties indicator files. Returns a dict with those fields. 
    """
    allowed_keys = {'name', 'description','factor','formula','weights','relatedEvent','category'}
    props = {}
    params = {}
    
    # Read each line, skip comments and blank lines
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            # Capture only allowed keys
            if key in allowed_keys:
                props[key] = value
            # Capture any param. entries into params dict
            elif key.startswith('param.'):
                raw = value.strip() #Get the value of the parameter
                try:                     # turn to int/float if we can
                    val = int(raw) if raw.isdigit() else float(raw)
                except ValueError: #if not a number, keep it as string
                    val = raw
   
                params[key[6:]] = val
        # Attach params if present
        if params:
            props['params'] = params
                
    return props


def build_indicator_def(props: dict, qm: str, path: str) -> dict:
    '''
    Builds a indicator definition from the loaded properties file.'''
    return {
        "filePath": path,
        "name": props["name"],
        "description": props.get("description",""),
        "factor": [m.strip() for m in props.get("factor","").split(",") if m],
        "formula": props.get("formula", "average"),
        "weights": [w.strip() for w in props.get('weights', '').split(',') if w.strip()],
        "quality_model": qm,
        "category": props.get("category", "NoCategory"),
    }

def build_indicators_index_per_qm(qm_root=QUALITY_MODELS_DIR):
    '''
    Scan all quality-model subfolders for indicator definitions.
    '''
    return scan_quality_model_folder(
        qm_root,
        subfolder="indicators",
        props_loader=load_required_fields_indicator,
        build_def=build_indicator_def
    )
    
    
