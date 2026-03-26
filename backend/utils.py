from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_fullname(user_account, default="N/A"):
    """Extract FullName from a UserAccount's related UserDetails safely."""
    if user_account and user_account.details:
        return user_account.details.FullName
    return default
