import os
import io
import sys
import csv
import getpass
import requests
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import json
import base64
import glob

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))
from app.ml_models import SimpleMLP

HUB_URL = "https://numerous-coyote-naman-limani-8961fadf.koyeb.app"

def test_mlp_model(local_model):
    print("\n[Testing Phase] Evaluating model on local tabular dataset...")
    features, labels = [], []
    
    # Inside test_mlp_model AND train_mlp_model:
    base_path = os.environ.get("EDGE_DATA_PATH", "edge_data")
    
    # First, look for any .csv file inside a 'tabular' subfolder
    csv_files = glob.glob(os.path.join(base_path, "tabular", "*.csv"))
    
    if not csv_files:
        # If not found, look for ANY .csv file directly in the folder they selected!
        csv_files = glob.glob(os.path.join(base_path, "*.csv"))
        
    if not csv_files:
        print(f"❌ Error: No CSV data found in {base_path}")
        return 0.0 # (Or sys.exit(1) for the train function)
        
    csv_path = csv_files[0] # Automatically grab the first CSV it finds!
    print(f"📁 Loading physical tabular data from {csv_path}...")
        
    try:
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            next(reader) 
            for row in reader:
                features.append([float(x) for x in row[:-1]])
                labels.append(int(row[-1]))
    except FileNotFoundError:
        print(f"❌ Error: test data not found at {csv_path}.")
        return 0.0

    tensor_x = torch.Tensor(features)
    tensor_y = torch.LongTensor(labels)
    dataset = TensorDataset(tensor_x, tensor_y)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)

    local_model.eval() 
    correct, total = 0, 0
    with torch.no_grad(): 
        for data, target in dataloader:
            outputs = local_model(data)
            _, predicted = torch.max(outputs.data, 1)
            total += target.size(0)
            correct += (predicted == target).sum().item()

    if total > 0:
        accuracy = 100 * correct / total
        print(f"📊 Local Model Accuracy: {accuracy:.2f}%")
    else:
        print("⚠️ No records found to test.")
        accuracy = 0.0
    return accuracy

def train_mlp_model(local_model, job_id, headers):
    print("\n--- Starting Local MLP Training Phase ---")
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(local_model.parameters(), lr=0.01)

    # Inside test_mlp_model AND train_mlp_model:
    base_path = os.environ.get("EDGE_DATA_PATH", "edge_data")
    
    # First, look for any .csv file inside a 'tabular' subfolder
    csv_files = glob.glob(os.path.join(base_path, "tabular", "*.csv"))
    
    if not csv_files:
        # If not found, look for ANY .csv file directly in the folder they selected!
        csv_files = glob.glob(os.path.join(base_path, "*.csv"))
        
    if not csv_files:
        print(f"❌ Error: No CSV data found in {base_path}")
        return 0.0 # (Or sys.exit(1) for the train function)
        
    csv_path = csv_files[0] # Automatically grab the first CSV it finds!
    print(f"📁 Loading physical tabular data from {csv_path}...")
        
    print(f"📁 Loading physical tabular data from {csv_path}...")
    features, labels = [], []
    
    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        next(reader)  
        for row in reader:
            features.append([float(x) for x in row[:-1]])
            labels.append(int(row[-1]))
            
    tensor_x = torch.Tensor(features)
    tensor_y = torch.LongTensor(labels)
    dataset = TensorDataset(tensor_x, tensor_y)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
    
    local_model.train()
    epochs = 3
    
    for epoch in range(epochs):
        total_loss = 0
        for batch_idx, (data, target) in enumerate(dataloader):
            optimizer.zero_grad()
            output = local_model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        avg_loss = total_loss / len(dataloader)
        print(f" -> Epoch {epoch+1}/{epochs} | Average Loss: {avg_loss:.4f}")

        try:
            payload = {"round": epoch + 1, "loss": avg_loss}
            requests.post(f"{HUB_URL}/training-jobs/{job_id}/telemetry", json=payload, headers=headers)
        except Exception as e:
            print(f"⚠️ Failed to send telemetry: {e}")
        
    print("✅ Local Training Completed! MLP weights updated.")
    return local_model

def run_mlp_pipeline():
    print("\n" + "="*45)
    print(" 🚀 FEDERHUB EDGE NODE CLIENT (MLP) ")
    print("="*45)
    
    if os.environ.get("HUB_MODE") == "UI":
        email = os.environ.get("HUB_EMAIL")
        password = os.environ.get("HUB_PASSWORD")
        job_id_str = os.environ.get("HUB_JOB_ID")
        
        if not email or not password or not job_id_str:
            print("❌ UI Error: Missing credentials.")
            sys.exit(1)
    else:
        email = input("👤 Enter your Client Email: ")
        password = getpass.getpass("🔑 Enter your Password: ")
        job_id_str = input("🎯 Enter the Job ID to join: ")
    
    try:
        job_id = int(job_id_str)
    except ValueError:
        print("❌ Invalid Job ID.")
        sys.exit(1)

    print(f"\nTargeting Hub: {HUB_URL}")

    # 1. Login
    print("\n[1/6] Authenticating with the Hub...")
    login_data = {"username": email, "password": password}
    response = requests.post(f"{HUB_URL}/login", data=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.json().get('detail')}")
        sys.exit(1)
        
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Successfully authenticated. JWT obtained.")

    try :
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        token_data = json.loads(base64.b64decode(payload))
        node_id = int(token_data.get("sub")) if token_data.get("sub") and str(token_data.get("sub")).isdigit() else abs(hash(email)) % 10000
    except:
        node_id = 999
    print(f"🔍 Assigned Edge Node ID: {node_id}")

    # 2. Verify Blueprint
    print(f"\n[2/6] Fetching Blueprint for JOB ID: {job_id}")
    job_response = requests.get(f"{HUB_URL}/training-jobs/{job_id}", headers=headers)
    if job_response.status_code != 200:
        print(f"❌ Failed to fetch job: {job_response.text}")
        sys.exit(1)
        
    template = job_response.json().get("model_template")
    if "MLP" not in template.upper():
        print(f"❌ Error: Hub requires {template}.")
        sys.exit(1)
    print(f"✅ Blueprint verified. Model architecture: {template}")

    # 3. HTTP REST Download (Bypasses Koyeb Firewall)
    print(f"\n[3/6] Downloading global MLP model from {HUB_URL}...")
    model_response = requests.get(f"{HUB_URL}/training-jobs/{job_id}/model", headers=headers)
    if model_response.status_code != 200:
        print(f"❌ Failed to download model: {model_response.text}")
        sys.exit(1)
        
    file_bytes = io.BytesIO(model_response.content)
    print("✅ HTTP stream complete. Model downloaded.")

    # 4. Local Training or Testing
    print("\n[4/6] Loading weights into PyTorch engine...")
    local_model = SimpleMLP()
    global_state_dict = torch.load(file_bytes, weights_only=True)
    local_model.load_state_dict(global_state_dict)
    print("✅ Global weights synchronized!")
    
    run_mode = os.environ.get("HUB_RUN_MODE", "train")
    if run_mode == "test":
        print("\n[INFO] Mode set to TEST ONLY. Skipping training and upload.")
        test_mlp_model(local_model)
        return
    
    updated_local_model = train_mlp_model(local_model, job_id, headers)
    test_mlp_model(updated_local_model)

    # 5. HTTP REST Upload (Bypasses Koyeb Firewall)
    print("\n[5/6] Uploading smarter MLP weights back via HTTP...")
    upload_buffer = io.BytesIO()
    torch.save(updated_local_model.state_dict(), upload_buffer)
    upload_buffer.seek(0)
    
    files = {"file": (f"job_{job_id}_node_{node_id}.pt", upload_buffer, "application/octet-stream")}
    
    try:
        upload_response = requests.post(f"{HUB_URL}/training-jobs/{job_id}/upload", headers=headers, files=files)
        if upload_response.status_code == 200:
            print(f"✅ Success! Hub responded: {upload_response.json().get('message')}")
        else:
            print(f"❌ Hub rejected the upload: {upload_response.text}")
    except Exception as e:
        print(f"❌ HTTP Upload failed: {e}")

if __name__ == "__main__":
    run_mlp_pipeline()