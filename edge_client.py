import requests
import io
import os
import torch
import sys
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader , TensorDataset , Dataset
from torchvision import datasets , transforms
import argparse
import grpc
import csv
# In a real-world scenario, the edge node would have its own independent copy 
# of the model classes. For our local simulation, we'll just import them from the Hub.
from app.ml_models import SimpleCNN , SimpleMLP


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))
import app.federated_pb2 as federated_pb2
import app.federated_pb2_grpc as federated_pb2_grpc


# HUB_URL = "http://host.docker.internal:8000"
# GRPC_URL = "host.docker.internal:50051"

HUB_URL = "http://127.0.0.1:8000"
GRPC_URL = "localhost:50051"

def train_local_model(local_model , template):
    print("\n ---Strating Local Training Phase---")

    # Standard PyTorch loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(local_model.parameters() , lr=0.01)

    # DATA INGESTION: Read physical files from the hard drive!
    if "CNN" in template.upper():
        print("Loading physical image data from edge_data/images ...")
        # Define how to process the images (resize and convert to PyTorch tensors)
        transform = transforms.Compose([
            transforms.Grayscale(num_output_channels = 1),
            transforms.Resize((28 , 28)),
            transforms.ToTensor()
        ])
        # ImageFolder automatically uses subdirectories as class labels
        dataset = datasets.ImageFolder(root="edge_data/images" , transform=transform)
        dataloader = DataLoader(dataset , batch_size=32 , shuffle=True)

    else :
        print("Loading tabular datar from edge_data/tabular ...")
        features = []
        labels = []

        # Read the CSV file row by row
        with open("edge_data/tabular/local_records.csv" , "r") as f :
            reader = csv.reader(f)
            next(reader) # Skip the header row
            for row in reader:
                # First 10 columns are features, last column is the target (0 or 1)
                features.append([float(x) for x in row[:-1]])
                labels.append(int(row[-1]))
        
        # Convert lists to PyTorch Tensors
        tensor_x = torch.Tensor(features)
        tensor_y = torch.Tensor(labels)

        dataset = TensorDataset(tensor_x , tensor_y)
        dataloader = DataLoader(dataset , batch_size=32 , shuffle=True)
    
    # ACTUAL TRAINING LOOP
    local_model.train()
    epochs = 3

    for epoch in range(epochs):
        total_loss = 0.0
        for batch_idx , (data , target) in enumerate(dataloader):
            optimizer.zero_grad()
            output = local_model(data)
            loss = criterion(output , target)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        avg_loss = total_loss / len(dataloader)
        print(f" -> Epoch {epochs + 1}/{epochs} | Average Loss: {avg_loss: .4f}")

    print("Local Training Completed! Edge model weights updated using Real data")
    return local_model




def run_edge_client(email , password , job_id):

    print(f"--- Starting EDGE NODE CLIENT ---")
    print(f"Targeting Hub: {HUB_URL}")

    # 1. AUTHENTICATE AND GET THE VIP WRISTBAND
    print("\n[1/5] Authenticating with the Hub..")
    login_data = {"username" : email , "password" : password}
    response = requests.post(f"{HUB_URL}/login" , data=login_data)

    if response.status_code != 200:
        print(f"Login Falied: {response.text}")
        sys.exit(1)

    token = response.json().get("access_token")
    headers = {"Authorization" : f"Bearer {token}"}
    print("Successfully authenticated. JWT obtained")

    # 2. FETCH THE JOB BLUEPRINT
    print(f"\n[2/5] Fetching Blueprint for JOB ID: {job_id}")

    job_response = requests.get(f"{HUB_URL}/training-jobs/" , headers=headers , params={"skip" : 0 , "limit" : 100})

    if job_response.status_code != 200 :
        print(f"Failed to fetech the jobs : {job_response.text}")
        sys.exit(1)

    # Find our specific job in the list
    jobs = job_response.json()
    target_job = next((job for job in jobs if job["id"] == job_id), None)

    if not target_job:
        print(f"Job {job_id} not found in the Hub")
        sys.exit(1)
    
    template = target_job.get("model_template" , "Unknown")
    print(f"Blueprint recieved. Model architecture required: {template}")

    # 3. DOWNLOAD THE GLOBAL MODEL WEIGHTS (Upgraded to GRPC)
    print(f"\n[3/5] Streaming global model from gRPC Hub at {GRPC_URL}...")

    # Open the high-speed channel to the gRPC server
    channel = grpc.insecure_channel(GRPC_URL)
    stub = federated_pb2_grpc.ModelTransferStub(channel)

    file_bytes = io.BytesIO()

    try :
        # Call the remote DownloadModel function
        request = federated_pb2.DownloadRequest(job_id=job_id)
        response_stream = stub.DownloadModel(request)

        # Catch the river of bytes and write them to our RAM buffer
        for chunk in response_stream:
            file_bytes.write(chunk.chunk_data)

        print("gRPC stream complete. Model downloaded.")
    
    except grpc.RpcError as e:
        print(f"gRPC download failed: {e.details()}")
        sys.exit(1)
    
    # Rewind the buffer so PyTorch can read it
    file_bytes.seek(0)


    # 4. LOAD INTO LOCAL PYTORCH MEMORY
    print("\n[4/5] Loading weights into local pytorch engine ...")

    # Instantiate the correct empty mathematical structure based on the blueprint
    if "CNN" in template.upper():
        local_model = SimpleCNN()
    else: 
        local_model = SimpleMLP()

    global_state_dict = torch.load(file_bytes , weights_only=True)

    # Inject the downloaded weights into our empty local model
    local_model.load_state_dict(global_state_dict)

    print("Global weights successfully synchronized !")
    print("\n ---Edge Node is ready for local training---")

    # Just to prove it worked, let's print the shape of the first layer's weights
    first_layer_name = list(global_state_dict.keys())[0]
    first_layer_shape = global_state_dict[first_layer_name].shape
    print(f"(Debug) Layer '{first_layer_name}' shape verified as : {first_layer_shape}")

    # --- NEW: TRIGGER LOCAL TRAINING ---
    updated_local_weight = train_local_model(local_model , template)

    # Let's verify the weights actually changed!
    new_first_layer_weights = updated_local_weight.state_dict()[first_layer_name]

    # We compare the original downloaded weights to the new trained weights
    are_weights_identical = torch.equal(global_state_dict[first_layer_name] , new_first_layer_weights)
    print(f"\n (Debug) Did the weights chnage during training ? {'No' if are_weights_identical else 'Yes'}")

    # 5. UPLOAD NEW WEIGHTS BACK TO THE HUB
    print("\n[5/5] Streaming smarter weights back to Hub via gRPC...")

    # Create an empty byte buffer in RAM
    buffer = io.BytesIO()

    # Save the updated PyTorch dictionary directly into that RAM buffer
    torch.save(updated_local_weight.state_dict() , buffer)

    # Rewind the buffer back to the beginning so requests can read it
    buffer.seek(0)

    # Create a Python Generator to chunk the file and stream it up
    def generate_chunks():
        chunk_size = 64 * 1024
        while True:
            piece = buffer.read(chunk_size)
            if not piece:
                break

            # We hardcode a dummy node_id=1 for now, just to prove the stream works
            yield federated_pb2.ModelChunk(job_id=job_id , node_id=1 , chunk_data=piece)
        
    try :
        # Pass the generator straight into the stub
        upload_response = stub.UploadModel(generate_chunks())

        if upload_response.success:
            print(f"Success! HUB responded: {upload_response.message}")
        else :
            print(f"HUB rejected the upload: {upload_response.message}")
    
    except grpc.RpcError as e :
        print(f"gRPC Upload failed: {e.details()}")
    
    finally :
        # Close the gRPC connection
        channel.close()


if __name__ == '__main__':
    # Set up the Argument Parser
    parser = argparse.ArgumentParser(description="Decentralized ML Hub - Edge Node Clien")
    
    # Define the required terminal arguments
    parser.add_argument("--email" , type=str , required=True , help="Your Registered Hub email address")
    parser.add_argument("--password" , type=str , required=True , help="Your Hub password")
    parser.add_argument("--job-id" , type=int , required=True , help="The ID of the federated training job to join")

    # Parse the arguments provided by the user in the terminal
    args = parser.parse_args()

    # Pass the user's terminal arguments into our function
    run_edge_client(args.email , args.password , args.job_id)
