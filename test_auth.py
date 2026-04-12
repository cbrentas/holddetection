import uuid
import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import User, RefreshToken
from app.core.settings import settings
from app.services.auth_service import (
    hash_password,
    verify_password,
    generate_access_token,
    decode_access_token,
    generate_refresh_token_plaintext,
    hash_refresh_token,
    verify_refresh_token_hash,
    create_persisted_refresh_token,
    rotate_refresh_token,
    revoke_refresh_token,
    revoke_token_family,
)

# Setup in-memory sqlite for testing DB interactions
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_user(db_session):
    user = User(
        email=f"test{uuid.uuid4()}@example.com",
        password_hash="dummy",
        display_name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user

def test_password_hashing():
    password = "supersecretpassword"
    hashed = hash_password(password)
    
    # Check that it's a valid argon2 hash
    assert hashed.startswith("$argon2")
    
    # Verify correctly
    assert verify_password(password, hashed) is True
    
    # Verify incorrectly
    assert verify_password("wrongpassword", hashed) is False

def test_access_token_generation_validation(mock_user):
    token = generate_access_token(mock_user)
    assert isinstance(token, str)
    assert len(token) > 0
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == str(mock_user.id)
    assert decoded["email"] == mock_user.email
    assert "exp" in decoded
    assert "iat" in decoded
    assert "jti" in decoded

def test_access_token_invalid():
    decoded = decode_access_token("invalid_token_string")
    assert decoded is None

def test_refresh_token_hashing():
    plaintext = generate_refresh_token_plaintext()
    assert len(plaintext) == 64
    
    hashed = hash_refresh_token(plaintext)
    assert plaintext != hashed
    
    assert verify_refresh_token_hash(plaintext, hashed) is True
    assert verify_refresh_token_hash("wrong", hashed) is False

def test_refresh_token_lifecycle(db_session, mock_user):
    metadata = {"user_agent": "pytest", "ip_address": "127.0.0.1"}
    
    # 1. Create
    plaintext, rt = create_persisted_refresh_token(db_session, mock_user, metadata)
    assert len(plaintext) == 64
    assert rt.user_id == mock_user.id
    assert rt.family_id is not None
    assert rt.revoked_at is None
    assert rt.replaced_by_token_id is None
    assert verify_refresh_token_hash(plaintext, rt.token_hash)
    
    db_session.refresh(rt)
    initial_rt_id = rt.id
    family_id = rt.family_id
    
    # 2. Rotate
    new_plaintext, new_rt = rotate_refresh_token(db_session, rt, {"ip_address": "192.168.1.1"})
    assert new_rt.id != initial_rt_id
    assert new_rt.family_id == family_id
    assert new_rt.ip_address == "192.168.1.1" # updated metadata
    assert new_rt.user_agent == "pytest" # inherited metadata
    
    db_session.refresh(rt)
    assert rt.revoked_at is not None
    assert rt.replaced_by_token_id == new_rt.id
    
    # 3. Revoke single token
    revoke_refresh_token(db_session, new_rt)
    db_session.refresh(new_rt)
    assert new_rt.revoked_at is not None

def test_revoke_token_family(db_session, mock_user):
    metadata = {"user_agent": "pytest", "ip_address": "127.0.0.1"}
    
    # Create a chain of 3 tokens
    _, rt1 = create_persisted_refresh_token(db_session, mock_user, metadata)
    _, rt2 = rotate_refresh_token(db_session, rt1, metadata)
    _, rt3 = rotate_refresh_token(db_session, rt2, metadata)
    
    db_session.refresh(rt2)
    
    # rt1 and rt2 are already revoked due to rotation
    assert rt1.revoked_at is not None
    assert rt2.revoked_at is not None
    assert rt3.revoked_at is None
    
    # Revoke family
    revoke_token_family(db_session, rt1.family_id)
    
    db_session.refresh(rt3)
    assert rt3.revoked_at is not None
