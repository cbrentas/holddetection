import abc

class BaseStorage(abc.ABC):
    @abc.abstractmethod
    def save_uploaded_image(self, upload_id: str, file_obj) -> str:
        """Save an uploaded image file-like object and return its URI."""
        pass

    @abc.abstractmethod
    def save_inference_result(self, job_id: str, image_bytes: bytes) -> str:
        """Save an annotated inference result (bytes) and return its URI."""
        pass

    @abc.abstractmethod
    def resolve_uri(self, uri: str) -> str:
        """Resolve a storage URI to a local path that can be opened for reading."""
        pass

    @abc.abstractmethod
    def make_uri(self, path: str) -> str:
        """Convert a local path into a storage URI."""
        pass

    @abc.abstractmethod
    def get_model_weights_path(self, uri: str) -> str:
        """Get a local path to model weights given its URI."""
        pass
