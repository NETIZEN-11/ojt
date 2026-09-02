from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

import boto3
from botocore.config import Config

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class StorageProvider(ABC):
    @abstractmethod
    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        pass


class S3StorageProvider(StorageProvider):
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.S3_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            self.client.create_bucket(Bucket=self.bucket)

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return f"{settings.S3_ENDPOINT_URL}/{self.bucket}/{key}"

    async def download(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    async def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    async def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expiration,
        )


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str | None = None):
        from app.core.config import get_settings

        settings = get_settings()
        self.base_path = base_path or settings.LOCAL_STORAGE_PATH or "/tmp/redteam-storage"  # nosec: dev default
        import os

        os.makedirs(self.base_path, exist_ok=True)

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        import os

        path = os.path.join(self.base_path, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return f"file://{path}"

    async def download(self, key: str) -> bytes:
        import os

        path = os.path.join(self.base_path, key)
        with open(path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> bool:
        import os

        path = os.path.join(self.base_path, key)
        try:
            os.remove(path)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        import os

        path = os.path.join(self.base_path, key)
        return os.path.exists(path)

    async def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        return await self.upload(key, b"")


class StorageProviderFactory:
    @staticmethod
    def create_provider(provider_type: str = "s3") -> StorageProvider:
        if provider_type == "s3":
            return S3StorageProvider()
        if provider_type == "local" or settings.EVAL_MODE == "local":
            return LocalStorageProvider()
        logger.warning("unknown_storage_provider", provider=provider_type)
        return LocalStorageProvider()
