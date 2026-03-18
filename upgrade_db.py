from app.database import engine
from sqlalchemy import text

# Connect directly to the database and inject the new column
# with engine.connect() as conn:
#     try :
#         conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;"))
#         conn.commit()
#         print("Success : 'is_admin' column added to the user table!")
    
#     except Exception as e :
#         print(f"Note: {e}")

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE job_metrics ADD COLUMN user_id INTEGER REFERENCES users(id);"))
        conn.commit()
        print(" Success: 'user_id' column added to job_metrics table!")
    except Exception as e:
        print(f" Notice: {e}")