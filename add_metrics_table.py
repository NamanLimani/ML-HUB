from app.database import engine
from app.models import base

# This command looks at models.py and creates any tables that don't exist yet
base.metadata.create_all(bind=engine)
print("✅ Success: 'job_metrics' table created in PostgreSQL!")