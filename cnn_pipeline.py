import os
import io
import sys
import requests
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
import getpass
import json
import base64

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))
from app.ml_models import SimpleCNN

HUB_URL = "https://numerous-coyote-naman-limani-8961fadf.koyeb.app"

def test_cnn_model(local_model):
    print("\n[Testing Phase] Evaluating model on local image dataset")
    transform = transforms.Compose([
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((28 , 28)),
        transforms.ToTensor()
    ])

    # Inside test_cnn_model AND train_cnn_model:
    base_path = os.environ.get("EDGE_DATA_PATH", "edge_data")
    img_path = os.path.join(base_path, "images")
    if not os.path.exists(img_path):
        img_path = base_path

    try:
        dataset = datasets.ImageFolder(root=img_path , transform=transform)
        dataloader = DataLoader(dataset , batch_size=32 , shuffle=True)
    except Exception as e:
        print(f"❌ Error: image data not found at {img_path}. Ensure it contains class subfolders.")
        return 0.0

    local_model.eval()
    correct = 0 
    total = 0

    with torch.no_grad():
        for data , target in dataloader:
            outputs = local_model(data)
            _ , predicted = torch.max(outputs.data , 1)
            total += target.size(0)
            correct += (predicted == target).sum().item()

    if total > 0:
        accuracy = 100 * correct / total
        print(f"📊 Local Model Accuracy {accuracy:.2f}%")
    else :
        print("⚠️ No images found for test")
        accuracy = 0.0
    return accuracy

def train_cnn_model(local_model , job_id , headers):
    print("\n--- Starting Local CNN Training Phase ---")
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(local_model.parameters(), lr=0.01)
    
    # Inside test_cnn_model AND train_cnn_model:
    base_path = os.environ.get("EDGE_DATA_PATH", "edge_data")
    img_path = os.path.join(base_path, "images")
    if not os.path.exists(img_path):
        img_path = base_path
        
    print(f"📁 Loading physical image data from {img_path}...")
    transform = transforms.Compose([
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((28, 28)),
        transforms.ToTensor()
    ])
    
    try:
        dataset = datasets.ImageFolder(root=img_path, transform=transform)
        dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
    except Exception as e:
        print(f"❌ Error loading training data: {e}")
        sys.exit(1)
    
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

        try :
            payload = {"round" : epoch + 1 , "loss" : avg_loss}
            requests.post(f"{HUB_URL}/training-jobs/{job_id}/telemetry" , json=payload , headers=headers)
        except Exception as e :
            print(f"⚠️ Failed to send telemetry {e}")
        
    print("✅ Local Training Completed! CNN weights updated.")
    return local_model

def run_cnn_pipeline():
    print("\n" + "="*45)
    print(" 🚀 FEDERHUB EDGE NODE CLIENT (CNN) ")
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

    try:
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
    if "CNN" not in template.upper():
        print(f"❌ Error: Hub requires {template}.")
        sys.exit(1)
    print(f"✅ Blueprint verified. Model architecture: {template}")

    # 3. HTTP REST Download (Bypasses Koyeb Firewall)
    print(f"\n[3/6] Downloading global CNN model from {HUB_URL}...")
    model_response = requests.get(f"{HUB_URL}/training-jobs/{job_id}/model", headers=headers)
    if model_response.status_code != 200:
        print(f"❌ Failed to download model: {model_response.text}")
        sys.exit(1)
        
    file_bytes = io.BytesIO(model_response.content)
    print("✅ HTTP stream complete. Model downloaded.")

    # 4. Local Training or Testing
    print("\n[4/6] Loading weights into PyTorch engine...")
    local_model = SimpleCNN()
    global_state_dict = torch.load(file_bytes, weights_only=True)
    local_model.load_state_dict(global_state_dict)
    print("✅ Global weights synchronized!")
    
    run_mode = os.environ.get("HUB_RUN_MODE", "train")
    if run_mode == "test":
        print("\n[INFO] Mode set to TEST ONLY. Skipping training and upload.")
        test_cnn_model(local_model)
        return
    
    updated_local_model = train_cnn_model(local_model, job_id, headers)
    test_cnn_model(updated_local_model)

    # 5. HTTP REST Upload (Bypasses Koyeb Firewall)
    print("\n[5/6] Uploading smarter CNN weights back via HTTP...")
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
    run_cnn_pipeline()