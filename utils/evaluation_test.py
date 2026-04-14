# app.py
import threading
from flask import Flask, request, jsonify
import logging
import os 

from logic.metrics_logic.metric_event_mapping import build_metrics_index_per_qm

from logic.factors_logic.factor_event_mapping import build_factors_index_per_qm

from logic.metrics_logic.metric_event_mapping import build_metrics_index_per_qm
from logic.metrics_logic.metric_recalculation import compute_metric_for_student, compute_metric_for_team

from logic.factors_logic.factor_recalculation import compute_factor, latest_metric_value

from logic.indicators_logic.indicator_event_mapping import build_indicators_index_per_qm

from config.load_config_file import get_event_meta
from config.logger_config import setup_logging
from API_calls.StudentDatafromLDRESTAPI import build_team_students_map
from config.quality_model_config import load_qualitymodel_map, choose_qualitymodel


from pymongo import MongoClient


from config.logger_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)




QUALITY_MODELS_DIR = os.getenv("QUALITY_MODELS_DIR", "QUALITY_MODELS")

app = Flask(__name__)

# Build the metrics event map at startup scaning all the quality models metrics subfolders
ALL_METRICS_BY_QM,  EVENT_METRICS_BY_QM  = build_metrics_index_per_qm(QUALITY_MODELS_DIR)

# Build the metrics event map at startup scaning all the quality models factors subfolders
ALL_FACTORS_BY_QM,  EVENT_FACTORS_BY_QM  = build_factors_index_per_qm(QUALITY_MODELS_DIR)

# Build the metrics event map at startup scaning all the quality models indicators subfolders
ALL_INDICATORS_BY_QM,  EVENT_INDICATORS_BY_QM  = build_indicators_index_per_qm(QUALITY_MODELS_DIR)

# Build the team->students map at startup
TEAM_STUDENTS_MAP = build_team_students_map()
TEAM_QUALITYMODEL_MAP = load_qualitymodel_map()


print(EVENT_INDICATORS_BY_QM)




event_type = "push" # "push" or "issue" or "userstory"
external_id = "LD_TEST_Project"
author_name = "LD_TEST_User"

# No funciona en mayusculas, solo en minusculas
quality_model="amep"
#team_name = event_data.get("team_name")

client = MongoClient("mongodb://localhost:27017")
db = client["event_dashboard"]
    
meta = get_event_meta(event_type)
logger.info(meta) #PUT THIS LATER IN DEBUG LEVEL




data_source= meta["data_source"]
students=TEAM_STUDENTS_MAP.get(external_id, {}).get(data_source, [])


    
# Retrieve the students for that team
logger.info(f"Event={event_type}, team with external_id={external_id}, students={students}")

# Retrieve the triggered metrics
triggered_metrics = EVENT_METRICS_BY_QM.get(quality_model, {}).get(event_type, {})

logger.info(f"Triggered metrics: {[m['name'] for m in triggered_metrics]}")



# Recompute each metric
for metric_def in triggered_metrics:
    scope = metric_def["scope"]
    if scope == "individual":
        for student_name in students:
            compute_metric_for_student(metric_def, event_type, student_name, team_name=external_id)
    elif scope == "team":  # scope == "team"
        compute_metric_for_team(metric_def, event_type, team_name=external_id,students=students)
    else: #scope == "individual_only"
        compute_metric_for_student(metric_def, event_type, author_name, team_name=external_id)
    

# RECALCULTION OF THE FACTORS
triggered_factors = EVENT_FACTORS_BY_QM.get(quality_model, {}).get(event_type, [])
logger.info(f"Triggered factors: {[f['name'] for f in triggered_factors]}")
        
for factor_def in triggered_factors:
    
    values= {} # Empty dictionary to store the values for each metric in the factor
    
    for metrics in factor_def["metric"]:
        
        print(f"metrics to use: {metrics}")
        #For each metric in the factor, we need to get the latest value for that metric
        # We need to store these values in a dictionary with the metric name as key and the value as value
        values[metrics] = latest_metric_value(external_id, metrics)
    
    logger.info(f"Values of the metrics of factor {factor_def['name']}: {values}")
    final_val= compute_factor(external_id, factor_def, values)



# RECALCULTION OF THE INDICATORS
triggered_indicators = EVENT_INDICATORS_BY_QM.get(quality_model, {}).get(event_type, [])
logger.info(f"Triggered factors: {[f['name'] for f in triggered_indicators]}")


from indicators_logic.indicator_recalculation import compute_indicator, latest_factor_value
for indicator_def in triggered_indicators:
    
    indicator_values= {} # Empty dictionary to store the values for each metric in the factor
    
    for factors in indicator_def["factor"]:
        #For each metric in the factor, we need to get the latest value for that metric
        # We need to store these values in a dictionary with the metric name as key and the value as value
        indicator_values[factors] = latest_factor_value(external_id, factors)
    
    print(indicator_values)
    logger.info(f"Values of the factors of indicator {indicator_def['name']}: {indicator_values}")
    final_val_indicator= compute_indicator(external_id, indicator_def, indicator_values)

