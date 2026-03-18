from sqlalchemy.orm import Session
from . import models , schemas
from passlib.context import CryptContext
import bcrypt

def create_organisation(db : Session , org : schemas.OrganisationCreate):
    # 1. Convert the Pydantic schema into a SQLAlchemy model
    db_org = models.Organisation(name = org.name)

    # 2. Add it to the database session (staging area)
    db.add(db_org)

    # 3. Commit the transaction to save it permanently in PostgreSQL
    db.commit()

    # 4. Refresh the instance to get the auto-generated ID and created_at timestamp
    db.refresh(db_org)

    return db_org


def get_password_hash(password : str):
    # 1. bcrypt requires bytes, so we encode the string
    pwd_bytes = password.encode('utf-8')

    # 2. Generate a random salt and hash the password
    hashed_bytes = bcrypt.hashpw(pwd_bytes , bcrypt.gensalt())

    # 3. Convert the bytes back into a string to save in PostgreSQL
    return hashed_bytes.decode('utf-8')

def create_user(db : Session , user : schemas.UserCreate):
    hash_pwd = get_password_hash(user.password)

    db_user = models.User(
        email = user.email,
        hashed_password = hash_pwd,
        role = user.role,
        organisation_id = user.organisation_id
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

def create_training_job(db : Session , job : schemas.TrainingJobCreate):
    db_job = models.TrainingJob(
        name = job.name,
        model_template = job.model_template,
        total_rounds = job.total_rounds,
        aggregation_algorithm = job.aggregation_algorithm,
        organisation_id = job.organisation_id
    )

    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    return db_job

# --- READ OPERATIONS (GET) ---

def get_organisation(db : Session , org_id : int):
    # .first() returns the first result it finds, or None if it doesn't exist
    return db.query(models.Organisation).filter(models.Organisation.id == org_id).first()

def get_organisations(db : Session , skip : int = 0 , limit : int = 100):
    # .offset(skip) skips the first X records. .limit() restricts how many come back.
    return db.query(models.Organisation).offset(skip).limit(limit).all()

def get_user(db : Session , user_id : int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_users(db : Session , skip : int = 0 , limit : int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def get_training_job(db : Session , job_id : int):
    return db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()

def get_training_jobs(db: Session , skip : int = 0 , limit : int = 100):
    return db.query(models.TrainingJob).offset(skip).limit(limit).all()

# --- UPDATE OPERATIONS (PUT) ---

def update_organisation(db : Session , org_id : int , org_update : schemas.OrganisationUpdate):
    db_org = get_organisation(db , org_id)
    if not db_org:
        return None
    
    # Extract only the fields the user actually sent in the request
    update_data = org_update.model_dump(exclude_unset=True)

    for key , value in update_data.items():
        setattr(db_org , key , value)

    db.commit()
    db.refresh(db_org)
    return db_org

def update_user(db : Session , user_id : int , user_update : schemas.UserUpdate):
    db_user = get_user(db , user_id)
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)

    # If the user is updating their password, we MUST hash it first!
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for key , value in update_data.items():
        setattr(db_user , key , value)

    db.commit()
    db.refresh(db_user)
    return db_user

def update_training_job(db : Session , job_id : int , job_update : schemas.TrainingJobUpdate):
    db_job = get_training_job(db , job_id)
    if not db_job:
        return None
    
    update_data = job_update.model_dump(exclude_unset=True)

    for key , value in update_data.items():
        setattr(db_job , key , value)
    
    db.commit()
    db.refresh(db_job)
    return db_job

# --- DELETE OPERATIONS (DELETE) ---

def delete_organisation(db: Session, org_id: int):
    db_org = get_organisation(db, org_id)
    if not db_org:
        return False # Tells the router it wasn't found
        
    db.delete(db_org)
    db.commit()
    return True # Deletion successful

def delete_user(db: Session, user_id: int):
    db_user = get_user(db, user_id)
    if not db_user:
        return False
        
    db.delete(db_user)
    db.commit()
    return True

def delete_training_job(db: Session, job_id: int):
    db_job = get_training_job(db , job_id)
    if not db_job:
        return False
        
    db.delete(db_job)
    db.commit()
    return True

def verify_password(plain_password : str , hashed_password : str):
    password_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes , hash_bytes)

def authenticate_user(db : Session , email : str , password : str):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return False
    
    if not verify_password(password , user.hashed_password):
        return False
    
    return user
