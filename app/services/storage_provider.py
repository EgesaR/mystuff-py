"""Storage provider implementations for local disk and S3/Cloudflare R2."""

import asyncio
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from botocore.config import Config
from fastapi import UploadFile

from app.core.config import settings


class BaseStorageProvider(ABC):
    """Abstract base class defining the required storage provider interface."""

    @abstractmethod
    async def upload(
        self,
        file: UploadFile,
        subfolder: str,
        filename: str,
    ) -> str:
        """Upload a file and return its accessible URL or relative path."""

    @abstractmethod
    async def delete(
        self,
        path_or_url: str,
    ) -> bool:
        """Delete a file by its path or URL."""


class LocalStorageProvider(BaseStorageProvider):
    """Handles storing and deleting files on the local filesystem."""

    def __init__(
        self,
        base_dir: str | Path | None = None,
        base_url: str = "/uploads",
    ) -> None:
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR)
        self.base_url = base_url.rstrip("/")

    async def upload(
        self,
        file: UploadFile,
        subfolder: str,
        filename: str,
    ) -> str:
        """Save an uploaded file to local disk asynchronously."""

        target_dir = self.base_dir / subfolder
        target_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = target_dir / filename

        await file.seek(0)

        def _write_file() -> None:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(
                    file.file,
                    buffer,
                )

        await asyncio.to_thread(_write_file)

        return (
            f"{self.base_url}/"
            f"{subfolder}/"
            f"{filename}"
        )

    async def delete(
        self,
        path_or_url: str,
    ) -> bool:
        """Delete a local file using its path or URL."""

        cleaned_path = path_or_url

        if cleaned_path.startswith(self.base_url):
            cleaned_path = cleaned_path[
                len(self.base_url):
            ].lstrip("/")

        target_path = (
            self.base_dir / cleaned_path
        ).resolve()

        # Prevent directory traversal attacks
        if not str(target_path).startswith(
            str(self.base_dir.resolve())
        ):
            return False

        if (
            target_path.exists()
            and target_path.is_file()
        ):
            target_path.unlink()
            return True

        return False


class S3StorageProvider(BaseStorageProvider):
    """Handles storing and deleting files in S3-compatible storage."""

    def __init__(self) -> None:
        try:
            import boto3  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "The 'boto3' package is required for S3 storage. "
                "Install it with 'uv add boto3'."
            ) from exc

        if not settings.S3_ACCESS_KEY_ID:
            raise ValueError(
                "Missing S3_ACCESS_KEY_ID"
            )

        if not settings.S3_SECRET_ACCESS_KEY:
            raise ValueError(
                "Missing S3_SECRET_ACCESS_KEY"
            )

        if not settings.S3_ENDPOINT_URL:
            raise ValueError(
                "Missing S3_ENDPOINT_URL"
            )

        self.s3_client: Any = boto3.client(  # pyright: ignore[reportUnknownMemberType]
            "s3",
            aws_access_key_id=getattr(settings, "S3_ACCESS_KEY_ID", None),
            aws_secret_access_key=getattr(
                settings, "S3_SECRET_ACCESS_KEY", None),
            endpoint_url=getattr(settings, "S3_ENDPOINT_URL", None),
            region_name=getattr(settings, "S3_REGION", "auto"),
            config=Config(
                connect_timeout=10,
                read_timeout=60,
                retries={"max_attempts": 3}
            )
        )
        self.bucket: str = getattr(
            settings,
            "S3_BUCKET_NAME",
            "mystuff-bucket",
        )

        self.custom_domain: str | None = getattr(
            settings,
            "S3_CUSTOM_DOMAIN",
            None,
        )

        self.endpoint_url: str | None = getattr(
            settings,
            "S3_ENDPOINT_URL",
            None,
        )

    async def upload(
        self,
        file: UploadFile,
        subfolder: str,
        filename: str,
    ) -> str:
        """Upload a file object to S3/R2 asynchronously."""

        object_name = (
            f"{subfolder}/{filename}"
        ).lstrip("/")

        await file.seek(0)

        def _upload_file() -> None:
            extra_args: dict[str, str] = {
                "ContentType": file.content_type or "application/octet-stream",
                "ContentDisposition": "attachment"
            }

            if file.content_type:
                extra_args["ContentType"] = (
                    file.content_type
                )

            self.s3_client.upload_fileobj(
                file.file,
                self.bucket,
                object_name,
                ExtraArgs=extra_args,
            )

        await asyncio.to_thread(
            _upload_file
        )

        # Prefer custom CDN/domain URL
        if self.custom_domain:
            return (
                f"{self.custom_domain.rstrip('/')}/"
                f"{object_name}"
            )

        # S3-compatible endpoint URL
        if self.endpoint_url:
            return (
                f"{self.endpoint_url.rstrip('/')}/"
                f"{self.bucket}/"
                f"{object_name}"
            )

        # Fallback
        return object_name

    async def delete(
        self,
        path_or_url: str,
    ) -> bool:
        """Delete an object from S3/R2 bucket."""

        parsed = urlparse(path_or_url)

        if parsed.scheme:
            object_key = parsed.path.lstrip("/")

            if object_key.startswith(
                f"{self.bucket}/"
            ):
                object_key = object_key[
                    len(self.bucket) + 1:
                ]


        else:
            object_key = path_or_url.lstrip("/")

        if not object_key:
            return False

        try:
            await asyncio.to_thread(
                self.s3_client.delete_object,
                Bucket=self.bucket,
                Key=object_key,
            )

            return True

        except Exception:  # pylint: disable=broad-exception-caught
            return False


_storage: BaseStorageProvider | None = None


def get_storage_provider() -> BaseStorageProvider:
    """
        Factory function to select storage provider.
        Return the configured storage provider singleton.
    """

    global _storage

    if _storage is None:
        provider_type = settings.STORAGE_PROVIDER.lower()

        if provider_type in ("s3", "r2", "cloud"):
            _storage = S3StorageProvider()
        else:
            _storage = LocalStorageProvider()
            
    assert _storage is not None
    
    return _storage


# # Global storage instance imported by StorageService
# storage = get_storage_provider()
