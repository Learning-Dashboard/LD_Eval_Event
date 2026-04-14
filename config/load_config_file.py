import os
import json
from typing import Optional, Dict, List


def load_sources_config()-> dict:
    '''
    Load the JSON configuration for event sources.
    '''
     # Determine config file path (env override or default)
    config_path = os.getenv("SOURCES_CONFIG", "config_files/sources_config.json")
    # Read and parse the JSON configuration
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)



def get_event_meta(event_type: str) -> Optional[Dict]:
    '''
    Retrieve metadata for a given event type from sources_config.
    '''       
    event_meta=load_sources_config().get(event_type)
    
    return event_meta


def get_available_events() -> List[str]:
    """
    Returns a list of all available event types from the sources_config.json file.
    """
    return list(load_sources_config().keys())