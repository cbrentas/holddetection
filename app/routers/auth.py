from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User, RefreshToken
from app.schemas import UserRegister, UserLogin, TokenResponse, RefreshRequest, UserProfile
from app.services import auth_service
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import datetime

router = APIRouter(prefix="/api/auth", tags=["auth"])

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = auth_service.validate_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user


@router.post("/register", response_model=TokenResponse)
def register(data: UserRegister, request: Request, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_password = auth_service.hash_password(data.password)
    
    user = User(
        email=email,
        password_hash=hashed_password,
        display_name=data.display_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    metadata = {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None
    }
    
    access_token = auth_service.generate_access_token(user)
    refresh_token_plain, _ = auth_service.create_persisted_refresh_token(db, user, metadata)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_plain,
        token_type="bearer"
    )

@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not auth_service.verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    user.last_login_at = datetime.datetime.utcnow()
    db.commit()
    
    metadata = {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None
    }
    
    access_token = auth_service.generate_access_token(user)
    refresh_token_plain, _ = auth_service.create_persisted_refresh_token(db, user, metadata)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_plain,
        token_type="bearer"
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    token_hash = auth_service.hash_refresh_token(data.refresh_token)
    
    existing_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not existing_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    if existing_token.revoked_at:
        # Simplification rule: reject the token, do not implement full family revocation yet
        raise HTTPException(status_code=401, detail="Token has been revoked")
        
    if existing_token.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")
        
    user = db.query(User).filter(User.id == existing_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid user")
        
    metadata = {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None
    }
    
    refresh_token_plain, new_rt = auth_service.rotate_refresh_token(db, existing_token, metadata)
    access_token = auth_service.generate_access_token(user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_plain,
        token_type="bearer"
    )

@router.post("/logout")
def logout(data: RefreshRequest, db: Session = Depends(get_db)):
    # According to rules: "Revoke current refresh token only"
    token_hash = auth_service.hash_refresh_token(data.refresh_token)
    existing_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    
    if existing_token and not existing_token.revoked_at:
        auth_service.revoke_refresh_token(db, existing_token)
        
    return {"status": "success"}

@router.get("/me", response_model=UserProfile)
def get_me(user: User = Depends(get_current_user)):
    return UserProfile(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )
