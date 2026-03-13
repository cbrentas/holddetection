import os
from urllib.parse import urlparse

def make_local_uri(path: str) -> str:
    """
    Convert a local file path into a file:// URI to explicitly mark it as local storage.
    Useful for future-proofing database fields that might later hold s3:// URIs.
    """
    absolute_path = os.path.abspath(path)
    return f"file://{absolute_path}"

def resolve_storage_uri(uri: str) -> str:
    """
    Resolve a storage URI (file://, s3://, etc) into a local path that can be opened.
    For local paths without a scheme, return as-is for backwards compatibility.
    """
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        return parsed.path
    elif parsed.scheme == "s3":
        raise NotImplementedError("S3 storage resolution not yet implemented")
    elif not parsed.scheme:
        # Fallback for old plain-path data
        return uri
    
    raise ValueError(f"Unsupported storage scheme: {parsed.scheme}")
