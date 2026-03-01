from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

from app.core.settings import settings

security = HTTPBasic()

def basic_auth(credentials: HTTPBasicCredentials = Depends(security)):

    is_correct_user = secrets.compare_digest(
        credentials.username,
        settings.API_USER,
    )

    is_correct_password = secrets.compare_digest(
        credentials.password,
        settings.API_PASSWORD,
    )

    if not (is_correct_user and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username