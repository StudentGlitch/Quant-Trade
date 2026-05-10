from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
import duckdb
from pathlib import Path
import uuid
from datetime import timedelta

from .auth_schemas import TokenResponse, UserCreate, UserResponse
from ..core.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user_token
from ...core.security_vault import SecurityVault

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"

def get_duckdb_conn():
    try:
        # Needs write access for users
        con = duckdb.connect(str(DB_PATH))
        
        # Ensure schema (Multi-Tenant PRD 11.2)
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR PRIMARY KEY,
                email VARCHAR UNIQUE NOT NULL,
                hashed_password VARCHAR NOT NULL,
                role VARCHAR DEFAULT 'INVESTOR',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                hashed_key VARCHAR NOT NULL,
                key_prefix VARCHAR,
                status VARCHAR DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS user_sub_ledgers (
                date DATE,
                user_id VARCHAR,
                strategy_name VARCHAR,
                allocated_capital DOUBLE,
                current_equity DOUBLE,
                daily_pnl DOUBLE,
                PRIMARY KEY (date, user_id, strategy_name)
            );
        """)
        
        yield con
    except duckdb.IOException as e:
        logger.error(f"Failed to connect to DuckDB for auth: {e}")
        yield None
    finally:
        if 'con' in locals() and con is not None:
            con.close()

@router.post("/auth/register", response_model=UserResponse)
def register_user(user: UserCreate, con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    try:
        # Check if user exists
        existing = con.execute("SELECT user_id FROM users WHERE email = ?", [user.email]).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
            
        user_id = str(uuid.uuid4())
        hashed_pw = SecurityVault.get_password_hash(user.password)
        
        # First user is ADMIN
        count = con.execute("SELECT count(*) FROM users").fetchone()[0]
        role = "ADMIN" if count == 0 else "INVESTOR"
        
        con.execute("""
            INSERT INTO users (user_id, email, hashed_password, role)
            VALUES (?, ?, ?, ?)
        """, [user_id, user.email, hashed_pw, role])
        
        logger.info(f"New user registered: {user.email} ({role})")
        
        return UserResponse(user_id=user_id, email=user.email, role=role)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    user_row = con.execute("SELECT user_id, email, hashed_password, role FROM users WHERE email = ?", [form_data.username]).fetchone()
    
    if not user_row or not SecurityVault.verify_password(form_data.password, user_row[2]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_row[1], "role": user_row[3], "user_id": user_row[0]}, expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in: {user_row[1]}")
    return {"access_token": access_token, "token_type": "bearer"}

def get_current_active_user(token_payload: dict = Depends(get_current_user_token), con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """Dependency to verify user exists and return their DB row."""
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    email = token_payload.get("sub")
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    user = con.execute("SELECT user_id, email, role FROM users WHERE email = ?", [email]).fetchone()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"user_id": user[0], "email": user[1], "role": user[2]}

def require_admin(current_user: dict = Depends(get_current_active_user)):
    """Dependency to enforce ADMIN role (PRD 11.1)."""
    if current_user.get("role") != "ADMIN":
        logger.warning(f"Unauthorized access attempt by {current_user.get('email')}")
        raise HTTPException(status_code=403, detail="Not enough permissions. ADMIN required.")
    return current_user
