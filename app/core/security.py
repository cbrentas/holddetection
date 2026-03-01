from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

# Replace later with real auth system
USERS = {
    "w0nts4y": "v3ryc00l"
}

def basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_password = USERS.get(credentials.username)

    if not correct_password or not secrets.compare_digest(
        correct_password, credentials.password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username