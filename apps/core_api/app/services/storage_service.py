import os
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from google.cloud import storage
import structlog

logger = structlog.get_logger()

class StorageProvider(ABC):
    @abstractmethod
    def store(self, content: bytes, filename: str) -> str:
        """Store content and return a URL/path."""
        pass

    @abstractmethod
    def get_content(self, filename: str) -> bytes:
        """Retrieve content by filename."""
        pass

class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store(self, content: bytes, filename: str) -> str:
        dest = self.base_dir / filename
        dest.write_bytes(content)
        return f"file://{dest}"

    def get_content(self, filename: str) -> bytes:
        dest = self.base_dir / filename
        if not dest.exists():
            raise FileNotFoundError(f"Local storage: {filename} not found.")
        return dest.read_bytes()

class GCSStorageProvider(StorageProvider):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = storage.Client()

    def store(self, content: bytes, filename: str) -> str:
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(f"carousels/{filename}")
        blob.upload_from_string(content, content_type="application/pdf")
        
        # In a real prod environment, we'd return a signed URL or public URL
        # For now, we return the gs:// URI or a generic public link if bucket is public
        return f"https://storage.googleapis.com/{self.bucket_name}/carousels/{filename}"

    def get_content(self, filename: str) -> bytes:
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(f"carousels/{filename}")
        if not blob.exists():
            raise FileNotFoundError(f"GCS storage: {filename} not found in bucket {self.bucket_name}")
        return blob.download_as_bytes()

def get_storage_provider(settings) -> StorageProvider:
    if settings.environment == "production" and settings.gcs_bucket_name:
        return GCSStorageProvider(settings.gcs_bucket_name)
    
    # Fallback to local storage
    base_dir = Path("/tmp/carousel_pdfs")
    return LocalStorageProvider(base_dir)
