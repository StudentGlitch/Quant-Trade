import os
from datetime import datetime
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

NEXTAUTH_SECRET = os.getenv("NEXTAUTH_SECRET")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

class NextAuthJWTPayload(BaseModel):
    email: str
    name: Optional[str] = None
    sub: str  # User ID
    iat: int
    exp: int

def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # In NextAuth, the token might be prefixed or wrapped depending on implementation
        # Here we assume a standard JWT since the PRD suggests HS256 and python-jose
        payload = jwt.decode(token, NEXTAUTH_SECRET, algorithms=[ALGORITHM])
        user_data = NextAuthJWTPayload(**payload)
        
        # Check expiration
        if datetime.fromtimestamp(user_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user_data
    except JWTError as e:
        print(f"JWT Decode Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
