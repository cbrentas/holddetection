import os
import shutil
from pathlib import Path
from urllib.parse import urlparse
from app.core.settings import settings
from app.core.storage.base import BaseStorage

class LocalStorage(BaseStorage):
    def __init__(self):
        Path(settings.STORAGE_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.STORAGE_RESULT_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.STORAGE_MODEL_DIR).mkdir(parents=True, exist_ok=True)

    def save_uploaded_image(self, upload_id: str, file_obj) -> str:
        file_path = Path(settings.STORAGE_UPLOAD_DIR) / f"{upload_id}.jpg"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)
        return self.make_uri(str(file_path))

    def save_inference_result(self, job_id: str, image_bytes: bytes) -> str:
        file_path = Path(settings.STORAGE_RESULT_DIR) / f"{job_id}.jpg"
        with open(file_path, "wb") as buffer:
            buffer.write(image_bytes)
        return self.make_uri(str(file_path))

    def resolve_uri(self, uri: str) -> str:
        parsed = urlparse(uri)
        if parsed.scheme == "file":
            return parsed.path
        elif parsed.scheme == "s3":
            raise NotImplementedError("S3 storage resolution not yet implemented")
        elif not parsed.scheme:
            # Fallback for old plain-path data
            return uri
        raise ValueError(f"Unsupported storage scheme: {parsed.scheme}")

    def make_uri(self, path: str) -> str:
        absolute_path = os.path.abspath(path)
        return f"file://{absolute_path}"

    def get_model_weights_path(self, uri: str) -> str:
        return self.resolve_uri(uri)
