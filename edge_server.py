import subprocess
from fastapi import FastAPI , HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

app = FastAPI()

# Allow the local React app to communicate with this server
app.add_middleware(
    CORSMiddleware,
    allow_origins = ['*'], # In production, restrict this to localhost:5174
    allow_credentials = True,
    allow_methods = ['*'],
    allow_headers = ['*']
)

class TrainingRequest(BaseModel):
    email : str
    password : str
    job_id : int
    data_path : str  # The absolute path on the user's Mac/PC (e.g., /Users/naman/edge_data)
    pipeline_type : str # "cnn" or "mlp"
    run_mode : str

@app.post("/start-local-training")
def start_local_training(req : TrainingRequest):
    """
    Receives credentials and file paths from the UI, constructs the Docker command,
    and runs it in the background using the secure Environment Variables.
    """
    script_name = "cnn_pipeline.py" if req.pipeline_type.lower() == 'cnn' else "mlp_pipeline.py"

    # Construct the Docker wormhole command
    docker_command = [
        "docker" , "run" , "--rm",
        "-v" , f"{req.data_path}:/workspace/edge_data", 
        "-e" , f"HUB_EMAIL={req.email}", 
        "-e" , f"HUB_PASSWORD={req.password}",
        "-e" , f"HUB_JOB_ID={req.job_id}",
        "-e" , f"HUB_RUN_MODE={req.run_mode}",
        "-e" , "HUB_MODE=UI",
        "federhub-client",
        "python" , "-u" , script_name 
    ]

    print(f"UI Triggered Training: Running {script_name} for Job {req.job_id}")
    
    def log_generator():
        yield "Initializing Local Intelligence Engine ... \n"
        try :
            # Run the Docker container
            # Note: In a fully fleshed app, we would stream this output back to the React UI via WebSockets.
            # For now, it will print to the terminal running this edge_server.
            process = subprocess.Popen(
                docker_command ,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1, # Line buffered
                universal_newlines=True
            )

            # Yield each line as soon as PyTorch prints it
            for line in iter(process.stdout.readline, ''):
                yield line

            process.stdout.close()
            process.wait() 

            if process.returncode == 0:
                yield "\n Training Cycle completed Successfully. \n"
            else :
                yield f"\n Process exited with error code {process.returncode}\n"
    
        except Exception as e :
            yield f"\n Failed to execute Docker: {str(e)}\n"

    return StreamingResponse(log_generator() , media_type="text/plain")
    
if __name__ == '__main__':
    import uvicorn
    # Notice we run this on port 8001 so it doesn't conflict with the main Hub on 8000!
    uvicorn.run(app , host="127.0.0.1" , port=8001)