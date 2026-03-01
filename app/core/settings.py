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

settings = Settings()