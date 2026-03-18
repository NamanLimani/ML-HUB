from app.database import SessionLocal
from app.models import User

db = SessionLocal()
# Find your user account
user = db.query(User).filter(User.email == "admin@gmail.com").first()

if user :
    user.is_admin = True
    db.commit()
    print(f"User {user.email} is now admin")
else :
    print("user not found")

db.close()