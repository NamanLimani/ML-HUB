from sqlalchemy import Column , String , ForeignKey , Integer , DateTime , Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import base

class Organisation(base):
    __tablename__ = "Organisations"

    id = Column(Integer , primary_key=True , index=True)
    name = Column(String , unique=True , index=True)
    created_at = Column(DateTime , default=datetime.utcnow)

    # Relationships: One organization can have multiple users and training jobs
    users = relationship("User" , back_populates="organisation")
    training_jobs = relationship("TrainingJob" , back_populates="organisation")

class User(base):
    __tablename__ = "users"

    id = Column(Integer , primary_key=True , index=True)
    email = Column(String , unique=True , index=True)
    hashed_password = Column(String)
    role = Column(String) # e.g., "Platform Admin", "ML Engineer", "Client Operator"
    organisation_id = Column(Integer , ForeignKey("Organisations.id"))
    is_admin = Column(Boolean , default=False) 

    # Relationship: Connects this user back to their specific organization
    organisation = relationship("Organisation" , back_populates="users")

class TrainingJob(base):
    __tablename__ = "training_jobs"

    id = Column(Integer , primary_key=True , index=True)
    name = Column(String , index=True)
    model_template = Column(String)
    total_rounds = Column(Integer , default=5)
    aggregation_algorithm = Column(String , default="FedAvg")
    organisation_id = Column(Integer , ForeignKey("Organisations.id"))

    # Relationship: Connects this job back to the organization that owns it
    organisation = relationship("Organisation" , back_populates="training_jobs") 


class JobMetrics(base):
    __tablename__ = "job_metrics"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("training_jobs.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    round_number = Column(Integer)
    metric_type = Column(String) # e.g., "local_loss" or "global_accuracy"
    value = Column(String) # Stored as a string to handle different float formats
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship to link back to the training job
    training_job = relationship("TrainingJob")
    user = relationship("User")
