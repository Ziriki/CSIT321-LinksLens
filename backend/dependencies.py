from fastapi import Depends, HTTPException, Request, status
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("FATAL: SECRET_KEY environment variable is not set.")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


############################################
# This function is to extract and verify the JWT from an HttpOnly cookie
# (web) or Authorization header (mobile), returning a dict with user_id
# and role_id on success, or raising 401 if the token is absent or invalid.
############################################
def get_current_user(request: Request) -> dict:
    token = None

    cookie_value = request.cookies.get("access_token")
    if cookie_value and cookie_value.startswith("Bearer "):
        token = cookie_value[7:]

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        role_id = payload.get("role")
        if user_id is None or role_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        return {"user_id": int(user_id), "role_id": int(role_id)}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


############################################
# This function is to return a FastAPI dependency factory that enforces
# one of the allowed role IDs, raising 403 if the current user's role is
# not in the permitted list.
# Role IDs: 1 = Administrator, 2 = Moderator, 3 = User
############################################
def require_role(*role_ids: int):
    ############################################
    # This function is to validate that the current user's role matches
    # one of the required role IDs and raise 403 if it does not.
    ############################################
    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role_id"] not in role_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )
        return current_user
    return checker
