import secrets
import string
import uuid
import datetime
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.core.settings import settings
from app.db.models import User, RefreshToken

ph = PasswordHasher()

def hash_password(plain_password: str) -> str:
    return ph.hash(plain_password)

def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False

def generate_access_token(user: User) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    expire = now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    claims = {
        "sub": str(user.id),
        "email": user.email,
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4())
    }
    
    encoded_jwt = jwt.encode(
        claims, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

def decode_access_token(token: str) -> dict | None:
    try:
        decoded_token = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return decoded_token
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None

def validate_access_token(token: str) -> dict | None:
    return decode_access_token(token)

def generate_refresh_token_plaintext() -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(64))

def hash_refresh_token(plaintext: str) -> str:
    # We can use argon2 for refresh tokens as well, or SHA256 since they are high entropy
    # Argon2 is preferred overall if performance is not an issue for RT verification.
    return ph.hash(plaintext)

def verify_refresh_token_hash(plaintext: str, token_hash: str) -> bool:
    try:
        return ph.verify(token_hash, plaintext)
    except VerifyMismatchError:
        return False

def create_persisted_refresh_token(
    db: Session, 
    user: User, 
    metadata: dict
) -> tuple[str, RefreshToken]:
    plaintext = generate_refresh_token_plaintext()
    token_hash = hash_refresh_token(plaintext)
    
    now = datetime.datetime.utcnow()
    expires_at = now + datetime.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        family_id=uuid.uuid4(),
        issued_at=now,
        expires_at=expires_at,
        user_agent=metadata.get("user_agent"),
        ip_address=metadata.get("ip_address")
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return plaintext, rt

def rotate_refresh_token(
    db: Session, 
    existing_token: RefreshToken, 
    metadata: dict
) -> tuple[str, RefreshToken]:
    # Update the old token to be revoked
    now = datetime.datetime.utcnow()
    existing_token.revoked_at = now
    
    # Create the new token, preserving the family id
    plaintext = generate_refresh_token_plaintext()
    token_hash = hash_refresh_token(plaintext)
    
    expires_at = now + datetime.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    new_rt = RefreshToken(
        user_id=existing_token.user_id,
        token_hash=token_hash,
        family_id=existing_token.family_id,
        issued_at=now,
        expires_at=expires_at,
        user_agent=metadata.get("user_agent") or existing_token.user_agent,
        ip_address=metadata.get("ip_address") or existing_token.ip_address
    )
    
    db.add(new_rt)
    db.flush()
    
    existing_token.replaced_by_token_id = new_rt.id
    
    db.commit()
    db.refresh(new_rt)
    
    return plaintext, new_rt

def revoke_refresh_token(db: Session, token: RefreshToken) -> None:
    token.revoked_at = datetime.datetime.utcnow()
    db.commit()

def revoke_token_family(db: Session, family_id: uuid.UUID) -> None:
    now = datetime.datetime.utcnow()
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id)
        .where(RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.commit()
