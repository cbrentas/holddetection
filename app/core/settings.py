from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "dev"
    DATABASE_URL: str

    STORAGE_UPLOAD_DIR: str = "storage/uploads"
    STORAGE_RESULT_DIR: str = "storage/results"
    STORAGE_MODEL_DIR: str = "storage/models"

    YOLO_IMAGE_SIZE: int = 640
    YOLO_CONF: float = 0.25

    ACTIVE_MODEL_ID: str | None = None

    API_USER: str
    API_PASSWORD: str

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    SECURE_COOKIES: bool = True

settings = Settings()