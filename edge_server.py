import os
import sys
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

# --- 1. THE NATIVE AI ENGINE HOOK ---
# If the executable is launched with a special flag, it transforms into the pipeline!
if len(sys.argv) > 1:
    if sys.argv[1] == "--run-cnn":
        from cnn_pipeline import run_cnn_pipeline
        run_cnn_pipeline()
        sys.exit(0)
    elif sys.argv[1] == "--run-mlp":
        from mlp_pipeline import run_mlp_pipeline
        run_mlp_pipeline()
        sys.exit(0)

# --- 2. THE NORMAL FASTAPI SERVER ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'], 
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

class TrainingRequest(BaseModel):
    email: str
    password: str
    job_id: int
    data_path: str  
    pipeline_type: str 
    run_mode: str

@app.post("/start-local-training")
def start_local_training(req: TrainingRequest):
    
    # Decide which pipeline flag to trigger
    worker_flag = "--run-cnn" if req.pipeline_type.lower() == 'cnn' else "--run-mlp"
    
    # Securely pass the credentials into the standalone environment
    custom_env = os.environ.copy()
    custom_env["HUB_EMAIL"] = req.email
    custom_env["HUB_PASSWORD"] = req.password
    custom_env["HUB_JOB_ID"] = str(req.job_id)
    custom_env["HUB_RUN_MODE"] = req.run_mode
    custom_env["HUB_MODE"] = "UI"
    
    # CRITICAL: Pass the exact folder path from the React UI into the pipeline
    custom_env["EDGE_DATA_PATH"] = req.data_path

    print(f"UI Triggered Native Training: {worker_flag} for Job {req.job_id}")
    
    def log_generator():
        yield "Initializing Native PyInstaller AI Engine (No Docker Required!)... \n"
        try:
            # We execute our own binary, but pass the worker flag!
            process = subprocess.Popen(
                [sys.executable, worker_flag],
                env=custom_env,
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
            else:
                yield f"\n Process exited with error code {process.returncode}\n"
    
        except Exception as e:
            yield f"\n Failed to execute Native Engine: {str(e)}\n"

    return StreamingResponse(log_generator(), media_type="text/plain")
    
if __name__ == '__main__':
    import uvicorn
    # Required for PyInstaller to handle subprocesses safely
    import multiprocessing
    multiprocessing.freeze_support()
    uvicorn.run(app, host="127.0.0.1", port=8001)