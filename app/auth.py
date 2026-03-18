import jwt
from datetime import datetime , timedelta
from typing import Optional
from fastapi import Depends , HTTPException , status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import models , database

SECRET_KRY = "super_secret_temporary_key_for_local_dev"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# This tells FastAPI that the token comes from the /login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data : dict , expire_delta : Optional[timedelta] = None):
    # Make a copy of the payload data so we don't accidentally modify the original
    to_encode = data.copy()

    # Set the expiration time
    if expire_delta:
        expire = datetime.utcnow() + expire_delta
    else :
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add the expiration time to the payload under the standard 'exp' claim
    to_encode.update({"exp" : expire})

    # Use the PyJWT library to encode the data into a secure string
    encoded_jwt = jwt.encode(to_encode , SECRET_KRY , algorithm=ALGORITHM)

    return encoded_jwt


def get_current_user(token : str = Depends(oauth2_scheme) , db : Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate" : "Bearer"}
    )

    try :
        # 1. Decode the token to read the payload
        payload = jwt.decode(token , SECRET_KRY , algorithms=[ALGORITHM])

        # 2. Extract the email (which we saved under the 'sub' key)
        email : str = payload.get("sub")
        if email is None:
            raise credentials_exception
    
    except jwt.InvalidTokenError:
        # If the token is expired or tampered with, PyJWT throws an error
        raise credentials_exception
    
    # 3. Check if the user actually still exists in the database
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user