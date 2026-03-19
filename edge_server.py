import subprocess
import os
from fastapi import FastAPI , HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins = ['*'], 
    allow_credentials = True,
    allow_methods = ['*'],
    allow_headers = ['*']
)

class TrainingRequest(BaseModel):
    email : str
    password : str
    job_id : int
    data_path : str  
    pipeline_type : str 
    run_mode : str

@app.post("/start-local-training")
def start_local_training(req : TrainingRequest):
    script_name = "cnn_pipeline.py" if req.pipeline_type.lower() == 'cnn' else "mlp_pipeline.py"

    # --- MAC DOCKER PATH FIX ---
    # Apple's sandbox hides the Docker path, so we find it manually.
    docker_bin = "/opt/homebrew/bin/docker" if os.path.exists("/opt/homebrew/bin/docker") else "/usr/local/bin/docker"
    if not os.path.exists(docker_bin):
        docker_bin = "docker" # Fallback just in case

    docker_command = [
        docker_bin , "run" , "--rm",
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
            process = subprocess.Popen(
                docker_command ,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

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
    uvicorn.run(app , host="127.0.0.1" , port=8001)