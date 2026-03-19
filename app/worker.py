import os
from celery import Celery
import torch
import copy
from .ml_models import SimpleCNN , SimpleMLP
import json
import redis
import time
import ssl

# --- 1. Clean the URL for Celery ---
RAW_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CLEAN_URL = RAW_URL.split("?")[0]

celery_app = Celery(
    "ml-tasks",
    broker=CLEAN_URL,
    backend=CLEAN_URL
)

# --- 2. THE MAGIC LINES: Tell Celery to ignore SSL directly in config ---
if CLEAN_URL.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {'ssl_cert_reqs': ssl.CERT_NONE}
    celery_app.conf.redis_backend_use_ssl = {'ssl_cert_reqs': ssl.CERT_NONE}

def federated_averaging(global_weights , local_weights_list):
    averaged_weights = copy.deepcopy(global_weights)
    for key in averaged_weights.keys():
        averaged_weights[key] = torch.stack([
            local_weights[key] for local_weights in local_weights_list
        ]).mean(dim=0)
    return averaged_weights

@celery_app.task(name="start_federated_training")
def start_federated_training(job_id: int, model_template: str):
    # --- 3. Tell Redis library to ignore SSL using the string "none" ---
    kwargs = {"ssl_cert_reqs": "none"} if CLEAN_URL.startswith("rediss://") else {}
    redis_client = redis.from_url(CLEAN_URL, **kwargs)
    
    channel_name = f"telemetry_job_{job_id}"

    print(f"\n[CELERY WORKER] -> Initializing federated training for Job ID: {job_id}")
    redis_client.publish(channel_name , json.dumps({"status" : "Initializing" , "message" : "Starting Job"}))
    
    if "CNN" in model_template.upper():
        print("[CELERY WORKER] -> Using CNN Architecture for Image Data.")
        global_model = SimpleCNN()
    elif "MLP" in model_template.upper():
        print("[CELERY WORKER] -> Using MLP Architecture for Numerical Data")
        global_model = SimpleMLP()
    else:
        print(f"[CELERY WORKER] -> Unknown template {model_template} Defaulting to MLP.")
        global_model = SimpleMLP()

    global_weights = global_model.state_dict()

    registry_dir = "app/model_registry"
    os.makedirs(registry_dir, exist_ok=True)
    baseline_path = os.path.join(registry_dir, f"global_model_job_{job_id}.pt")
    
    torch.save(global_weights, baseline_path)
    print(f"[CELERY WORKER] -> Round 0 baseline model created in registry.")

    required_nodes = 1 
    uploaded_dir = "app/uploaded_weights"
    os.makedirs(uploaded_dir , exist_ok=True)

    print(f"[CELERY WORKER] -> waiting for {required_nodes} real edge node(s) to upload weights")
    redis_client.publish(channel_name , json.dumps({
        "Status" : "Waiting",
        "message" : f"Listening for {required_nodes} edge node(s) on the network..."
    }))

    uploaded_file = []
    while len(uploaded_file) < required_nodes:
        all_file = os.listdir(uploaded_dir)
        uploaded_file = [f for f in all_file if f.startswith(f"job_{job_id}_node_")]
        if len(uploaded_file) < required_nodes:
            time.sleep(5)
    
    print("\n[Celery Worker] -> Required Weights received! Loading into memory..")
    redis_client.publish(channel_name , json.dumps({"status" : "aggregating" , "message" : "Real weights received! Calculating FedAvg"}))

    real_local_weights = []
    for file_name in uploaded_file:
        file_path = os.path.join(uploaded_dir , file_name)
        state_dict = torch.load(file_path , weights_only=True)
        real_local_weights.append(state_dict)
        print(f" -> Loaded {file_name}")

    new_global_weights = federated_averaging(global_weights , real_local_weights)
    global_model.load_state_dict(new_global_weights)

    registry_dir = "app/model_registry"
    os.makedirs(registry_dir , exist_ok=True)
    file_path = os.path.join(registry_dir , f"global_model_job_{job_id}.pt")
    torch.save(global_model.state_dict() , file_path)

    for file_name in uploaded_file:
        os.remove(os.path.join(uploaded_dir , file_name))

    print(f"[CELERY WORKER] -> Cleaned Up old edge files")

    redis_client.publish(channel_name , json.dumps({"status" : "Completed" , "message" : "Aggregation cycle finished !"}))
    print(f"[CELERY WORKER] -> Job Id: {job_id} aggregation cycle completed!\n")

    return {"job_id" : job_id , "status" : "completed"}