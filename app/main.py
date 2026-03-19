from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os
import json
import redis
import redis.asyncio as aioredis

from .database import base, get_db, engine
from . import models, schemas, crud, auth 
from .worker import start_federated_training, celery_app

# Initialize Database
models.base.metadata.create_all(bind=engine)

app = FastAPI(
    title='Decentralized ML Hub API',
    description='Central Orchestration layer for federated learning',
    version='1.0.0'
)

# --- Configure CORS ---
origins = [
    "http://localhost:5173",    # Admin Hub UI
    "http://127.0.0.1:5173",
    "http://localhost:5174",    # NEW: Edge Client UI
    "http://127.0.0.1:5174",    # NEW: Edge Client UI
    "https://ml-hub-hard.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins= origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"]  
)

def get_redis_client(is_async=False):
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # If using rediss:// (Upstash), we must pass ssl_cert_reqs as None (the code version of CERT_NONE)
    kwargs = {"ssl_cert_reqs": None} if url.startswith("rediss://") else {}
    
    if is_async:
        return aioredis.from_url(url, decode_responses=True, **kwargs)
    return redis.from_url(url, decode_responses=True, **kwargs)

# --- SYSTEM HEALTH ROUTES ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the Decentralized ML Hub API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Hub is operational"}

@app.get("/db-status")
def test_db(db: Session = Depends(get_db)):
    return {"status": "connected", "message": "Successfully connected to PostgreSQL"}

# --- AUTHENTICATION & IDENTITY ---
@app.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT access token."""
    user = crud.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.UserResponse)
def get_current_user_profile(current_user: models.User = Depends(auth.get_current_user)):
    """Returns the profile of the currently authenticated user based on their JWT."""
    return current_user

# --- CREATE ROUTES (POST) ---
@app.post("/organisations/", response_model=schemas.OrganisationResponse)
def create_organisation(org: schemas.OrganisationCreate, db: Session = Depends(get_db)):
    return crud.create_organisation(db=db, org=org)

@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db=db, user=user)

@app.post("/training-jobs/", response_model=schemas.TrainingJobResponse)
def create_training_job(job: schemas.TrainingJobCreate, db: Session = Depends(get_db)):
    return crud.create_training_job(db=db, job=job)

@app.post("/training-jobs/{job_id}/start")
def trigger_training_job(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden. Only Hub administrator can start training cycles.")
    
    job = db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    task = start_federated_training.delay(job.id, job.model_template)
    return {"message": f"Training Job {job_id} queued.", "task_id": task.id}

@app.post("/training-jobs/{job_id}/upload")
async def upload_local_weights(job_id: int, file: UploadFile = File(...), current_user: models.User = Depends(auth.get_current_user)):
    upload_dir = "app/uploaded_weights"
    os.makedirs(upload_dir, exist_ok=True)
    file_location = f"{upload_dir}/job_{job_id}_node_{current_user.id}.pt"

    with open(file_location, "wb+") as file_object:
        file_object.write(await file.read())
    
    print(f"[Hub] Received Updated weights for job {job_id} from user {current_user.id}")
    return {"message": "Local weights successfully uploaded.", "filename": file.filename}

@app.post("/training-jobs/{job_id}/telemetry")
def receive_telemetry(
    job_id: int, 
    payload: dict, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user) # <--- The JWT tells us who this is!
):
    """
    Saves live training metrics to PostgreSQL AND publishes them to Redis.
    """
    try:
        # 1. Save to PostgreSQL for permanent history (NOW WITH USER ID)
        new_metric = models.JobMetrics(
            job_id=job_id,
            user_id=current_user.id, # <--- NEW: Save the identity of the uploader!
            round_number=payload.get("round"),
            metric_type="local_loss",
            value=str(payload.get("loss"))
        )
        db.add(new_metric)
        db.commit()

        payload["client_email"] = current_user.email

        # 2. Publish to Redis for the live WebSocket stream
        r = get_redis_client(is_async=False)
        r.publish(f"telemetry_job_{job_id}", json.dumps(payload))
        
        return {"status": "Telemetry saved and broadcasted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- READ ROUTES (GET) ---
@app.get("/organisations/", response_model=List[schemas.OrganisationResponse])
def read_organisations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_organisations(db, skip=skip, limit=limit)

@app.get("/organisations/{org_id}", response_model=schemas.OrganisationResponse)
def read_single_organisation(org_id: int, db: Session = Depends(get_db)):
    db_org = crud.get_organisation(db, org_id=org_id)
    if db_org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return db_org

@app.get("/users/", response_model=List[schemas.UserResponse])
def get_all_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Admin-only endpoint to fetch all registered edge nodes/clients."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized. Admins only.")
    return db.query(models.User).all()

@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def read_single_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/training-jobs/", response_model=List[schemas.TrainingJobResponse])
def read_all_training_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_training_jobs(db, skip=skip, limit=limit)

@app.get("/training-jobs/{job_id}", response_model=schemas.TrainingJobResponse)
def read_single_training_job(job_id: int, db: Session = Depends(get_db)):
    db_job = crud.get_training_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Training Job not found")
    return db_job

@app.get("/training-jobs/{job_id}/model")
def download_global_model(job_id: int, current_user: models.User = Depends(auth.get_current_user)):
    file_path = f"app/model_registry/global_model_job_{job_id}.pt"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model file not found.")
    return FileResponse(path=file_path, media_type="application/octet-stream", filename=f"global_model_job_{job_id}.pt")

@app.get("/training-jobs/{job_id}/telemetry")
def get_telemetry_history(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    metrics = db.query(models.JobMetrics).filter(models.JobMetrics.job_id == job_id).order_by(models.JobMetrics.round_number).all()
    history = []
    for m in metrics:
        if m.metric_type == "local_loss":
            history.append({
                "round": f"Round {m.round_number}", 
                "loss": float(m.value),
                # --- NEW: Pull the email from the database relationship ---
                "client_email": m.user.email if m.user else "Unknown Node"
            })
    return history
    return history

@app.get("/tasks/{task_id}")
def get_task_status(task_id: str, current_user: models.User = Depends(auth.get_current_user)):
    task_result = celery_app.AsyncResult(task_id)
    return {"task_id": task_id, "status": task_result.status, "result": task_result.result}

@app.get("/metrics/history")
def get_audit_history(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Returns the training upload history.
    Admins see all network history. Clients only see their own uploads.
    """
    # Create a database query joining the Metrics, the User who sent them, and the Job
    query = db.query(
        models.JobMetrics, 
        models.User.email, 
        models.TrainingJob.name
    ).join(
        models.User, models.JobMetrics.user_id == models.User.id
    ).join(
        models.TrainingJob, models.JobMetrics.job_id == models.TrainingJob.id
    )
    
    # SECURITY: If the user is NOT an admin, filter out everyone else's data
    if not current_user.is_admin:
        query = query.filter(models.JobMetrics.user_id == current_user.id)
        
    # Sort by newest first
    metrics = query.order_by(models.JobMetrics.timestamp.desc()).all()
    
    # Format the data for React
    history = []
    for metric, user_email, job_name in metrics:
        history.append({
            "id": metric.id,
            "job_name": job_name,
            "round_number": metric.round_number,
            "loss": metric.value,
            "timestamp": metric.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "uploader": user_email
        })
        
    return history

# --- UPDATE ROUTES (PUT) ---
@app.put("/organisations/{org_id}", response_model=schemas.OrganisationResponse)
def update_organisation(org_id: int, org_update: schemas.OrganisationUpdate, db: Session = Depends(get_db)):
    db_org = crud.update_organisation(db, org_id=org_id, org_update=org_update)
    if db_org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return db_org

@app.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = crud.update_user(db, user_id=user_id, user_update=user_update)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.put("/training-jobs/{job_id}", response_model=schemas.TrainingJobResponse)
def update_training_job(job_id: int, job_update: schemas.TrainingJobUpdate, db: Session = Depends(get_db)):
    db_job = crud.update_training_job(db, job_id=job_id, job_update=job_update)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Training Job not found")
    return db_job

# --- SECURE DELETE ROUTES (ADMIN ONLY) ---
@app.delete("/organisations/{org_id}")
def delete_organisation(org_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized.")
    
    users_in_org = db.query(models.User).filter(models.User.organisation_id == org_id).first()
    jobs_in_org = db.query(models.TrainingJob).filter(models.TrainingJob.organisation_id == org_id).first()
    
    if users_in_org or jobs_in_org:
        raise HTTPException(status_code=400, detail="Cannot delete organization. Delete attached clients and jobs first.")
        
    org_to_delete = db.query(models.Organisation).filter(models.Organisation.id == org_id).first()
    if not org_to_delete:
        raise HTTPException(status_code=404, detail="Organization not found.")
        
    db.delete(org_to_delete)
    db.commit()
    return {"status": "Organization deleted successfully."}

@app.delete("/users/{target_user_id}")
def delete_user(target_user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized. Admins only.")
    
    if current_user.id == target_user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")

    user_to_delete = db.query(models.User).filter(models.User.id == target_user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found.")
        
    db.delete(user_to_delete)
    db.commit()
    return {"status": "Client successfully removed from the network."}

@app.delete("/training-jobs/{job_id}")
def delete_training_job(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized.")
        
    job_to_delete = db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
    if not job_to_delete:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    db.query(models.JobMetrics).filter(models.JobMetrics.job_id == job_id).delete()
        
    db.delete(job_to_delete)
    db.commit()
    return {"status": "Training job deleted successfully."}

# --- WEBSOCKET TELEMETRY ---
@app.websocket("/ws/telemetry/{job_id}")
async def websocket_telemetry(websocket: WebSocket, job_id: int):
    await websocket.accept()
    redis_client = get_redis_client(is_async=True)
    pubsub = redis_client.pubsub()
    channel_name = f"telemetry_job_{job_id}"
    await pubsub.subscribe(channel_name)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
                data = json.loads(message["data"])
                if data.get("status") == "completed":
                    break
    except WebSocketDisconnect:
        print(f"Client disconnected from telemetry stream for job {job_id}")
    finally:
        await pubsub.unsubscribe(channel_name)
        await redis_client.close()
        try:
            await websocket.close()
        except Exception:
            pass