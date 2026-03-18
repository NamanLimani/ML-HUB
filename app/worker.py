import os
from celery import Celery
import torch
import copy
from .ml_models import SimpleCNN , SimpleMLP
import json
import redis
import time

# --- NEW: Fetch Cloud Redis or Fallback to Local ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize the Celery application
celery_app = Celery(
    "ml-tasks",
    broker= REDIS_URL,
    backend=REDIS_URL
)

def federated_averaging(global_weights , local_weights_list):
    """
    Takes the global model weights and a list of local model weights from edge nodes.
    Returns the new averaged global weights.
    """
    averaged_weights = copy.deepcopy(global_weights)

    # Iterate through every layer/parameter in the model
    for key in averaged_weights.keys():
        # Stack all the local tensors for this specific layer and calculate the mean
        averaged_weights[key] = torch.stack([
            local_weights[key] for local_weights in local_weights_list
        ]).mean(dim=0)
    return averaged_weights

# The @celery_app.task decorator registers this function as a background job
@celery_app.task(name="start_federated_training")
def start_federated_training(job_id: int, model_template: str):
    """
    Simulates a long-running federated training cycle.
    """
    redis_client = redis.from_url(REDIS_URL)
    channel_name = f"telemetry_job_{job_id}"

    print(f"\n[CELERY WORKER] -> Initializing federated training for Job ID: {job_id}")
    redis_client.publish(channel_name , json.dumps({"status" : "Initializing" , "message" : "Starting Job"}))
    
    # Dynamically handle your two distinct model architectures!
    # 1. Initialize the correct Global Model based on the template
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

    # --- NEW FIX: CREATE ROUND 0 BASELINE ---
    registry_dir = "app/model_registry"
    os.makedirs(registry_dir, exist_ok=True)
    baseline_path = os.path.join(registry_dir, f"global_model_job_{job_id}.pt")
    
    # Save the fresh, un-trained model so the edge node always has a starting point!
    torch.save(global_weights, baseline_path)
    print(f"[CELERY WORKER] -> Round 0 baseline model created in registry.")

    # --- NEW: TRUE AGGREGATION GATE ---
    required_nodes = 1 # We only need 1 real edge node to trigger the math for this test
    uploaded_dir = "app/uploaded_weights"
    os.makedirs(uploaded_dir , exist_ok=True)

    print(f"[CELERY WORKER] -> waiting for {required_nodes} real edge node(s) to upload weights")
    redis_client.publish(channel_name , json.dumps({
        "Status" : "Waiting",
        "message" : f"Listening for {required_nodes} edge node(s) on the network..."
    }))

    # 2. The Polling Loop (Wait for real files to arrive)
    uploaded_file = []
    while len(uploaded_file) < required_nodes:
        # Check the folder for files matching this specific job
        all_file = os.listdir(uploaded_dir)
        uploaded_file = [f for f in all_file if f.startswith(f"job_{job_id}_node_")]

        if len(uploaded_file) < required_nodes:
            time.sleep(5)
    
    print("\n[Celery Worker] -> Required Weights received! Loading into memory..")
    redis_client.publish(channel_name , json.dumps({"status" : "aggregating" , "message" : "Real weights received! Calculating FedAvg"}))

    # 3. Load the Real Weights
    real_local_weights = []
    for file_name in uploaded_file:
        file_path = os.path.join(uploaded_dir , file_name)
        state_dict = torch.load(file_path , weights_only=True)
        real_local_weights.append(state_dict)
        print(f" -> Loaded {file_name}")

    # 4. Perform Federated Averaging on the REAL data!
    new_global_weights = federated_averaging(global_weights , real_local_weights)
    global_model.load_state_dict(new_global_weights)

    # 5. Save the New Global Model
    registry_dir = "app/model_registry"
    os.makedirs(registry_dir , exist_ok=True)
    file_path = os.path.join(registry_dir , f"global_model_job_{job_id}.pt")
    torch.save(global_model.state_dict() , file_path)

    # 6. Cleanup (Delete the edge node files so we are ready for the next round)
    for file_name in uploaded_file:
        os.remove(os.path.join(uploaded_dir , file_name))

    print(f"[CELERY WORKER] -> Cleaned Up old edge files")

    redis_client.publish(channel_name , json.dumps({"status" : "Completed" , "message" : "Aggregation cycle finished !"}))
    print(f"[CELERY WORKER] -> Job Id: {job_id} aggregation cycle completed!\n")

    return {"job_id" : job_id , "status" : "completed"}

    