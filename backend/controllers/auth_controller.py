from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone
import os # Import os to read environment variables
from dotenv import load_dotenv # Import this to load the .env file

# Import custom files
import models
import schemas
from database import get_db

load_dotenv() # Load the variables from the .env file

# Create a router for this controller
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

#########################################################
# Security settings for JWT and password hashing
#########################################################
# Pull the highly sensitive secret key from the environment
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("FATAL ERROR: SECRET_KEY environment variable is not set!")

# Pull configuration variables with safe fallbacks for local development
ALGORITHM = os.getenv("ALGORITHM", "HS256")

try:
    # Cast this to an integer for timedelta to work properly
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 120))
except ValueError:
    print("Warning: ACCESS_TOKEN_EXPIRE_MINUTES is not a valid integer. Defaulting to 120.")
    ACCESS_TOKEN_EXPIRE_MINUTES = 120

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Helper function to generate the token
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

#########################################################
# Login function for both Web and Mobile clients
#########################################################
@router.post("/login", response_model=schemas.TokenResponse)
def login(credentials: schemas.UserLogin, response: Response, db: Session = Depends(get_db)):
    # 1. Find the user by email
    user = db.query(models.UserAccount).filter(models.UserAccount.EmailAddress == credentials.EmailAddress).first()
    
    # 2. Verify user exists and password matches
    if not user or not pwd_context.verify(credentials.Password, user.PasswordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # 3. Check if account is active
    if not user.IsActive:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # 4. Generate the JWT Token payload
    token_data = {"sub": str(user.UserID), "role": user.RoleID}
    token = create_access_token(token_data)

    # 5. Route the response based on the platform!
    if credentials.ClientType == models.ClientTypeEnum.WEB:
        # For Web: Set an HttpOnly cookie. The browser handles it automatically.
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token}",
            httponly=True,
            secure=False, # Set to True if using HTTPS in production
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return {"message": "Web login successful"}
        
    elif credentials.ClientType == models.ClientTypeEnum.MOBILE:
        # For Mobile: Return the token directly so React Native can save it
        return {
            "access_token": token,
            "token_type": "bearer",
            "message": "Mobile login successful"
        }

#########################################################
# Logout function for both Web and Mobile clients
#########################################################
@router.post("/logout")
def logout(client_type: schemas.ClientTypeEnum, response: Response):
    # If the user is on the web, we tell the browser to delete the cookie
    if client_type == models.ClientTypeEnum.WEB:
        response.delete_cookie("access_token")
        return {"message": "Web logout successful. Cookie cleared."}
        
    # If mobile, the backend does nothing. 
    # The React Native app just deletes the token from its own local storage!
    return {"message": "Mobile logout successful. Please clear local token."}