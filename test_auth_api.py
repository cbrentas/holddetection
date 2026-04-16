import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db

# Setup in-memory sqlite for testing DB interactions
engine = create_engine(
    "sqlite://", 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def test_register_success(client):
    response = client.post("/api/auth/register", json={
        "email": "api_test@example.com",
        "password": "password123",
        "display_name": "API Test"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_register_duplicate(client):
    response = client.post("/api/auth/register", json={
        "email": "api_test@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 400

def test_login_success(client):
    response = client.post("/api/auth/login", json={
        "email": "api_test@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

def test_login_failure(client):
    response = client.post("/api/auth/login", json={
        "email": "api_test@example.com",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401

def test_me_success(client):
    # First login
    login_response = client.post("/api/auth/login", json={
        "email": "api_test@example.com",
        "password": "password123"
    })
    token = login_response.json()["access_token"]
    
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "api_test@example.com"
    assert data["display_name"] == "API Test"
    assert "id" in data

def test_refresh_success(client):
    # First login
    login_response = client.post("/api/auth/login", json={
        "email": "api_test@example.com",
        "password": "password123"
    })
    refresh_token = login_response.json()["refresh_token"]
    
    response = client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

def test_refresh_failure_invalid(client):
    response = client.post("/api/auth/refresh", json={
        "refresh_token": "invalid_refresh_token"
    })
    assert response.status_code == 401

def test_logout_success(client):
    # Login to get a token
    login_response = client.post("/api/auth/login", json={
        "email": "api_test@example.com",
        "password": "password123"
    })
    refresh_token = login_response.json()["refresh_token"]
    
    # Logout
    logout_response = client.post("/api/auth/logout", json={
        "refresh_token": refresh_token
    })
    assert logout_response.status_code == 200
    
    # Try to refresh with the logged out token
    refresh_response = client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert refresh_response.status_code == 401
