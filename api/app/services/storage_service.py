"""Storage service for managing files in MinIO."""

import logging
import os
from datetime import timedelta
from io import BytesIO
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file storage in MinIO."""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket_name: str | None = None,
        secure: bool = False,
    ):
        """
        Initialize the StorageService with MinIO connection.

        Args:
            endpoint: MinIO endpoint (default from env: MINIO_ENDPOINT)
            access_key: MinIO access key (default from env: MINIO_ACCESS_KEY)
            secret_key: MinIO secret key (default from env: MINIO_SECRET_KEY)
            bucket_name: Bucket name (default from env: MINIO_BUCKET or 'auditcaseos')
            secure: Use HTTPS (default: False for local dev)
        """
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.bucket_name = bucket_name or os.getenv("MINIO_BUCKET", "auditcaseos")
        self.secure = secure or os.getenv("MINIO_SECURE", "false").lower() == "true"

        self.client: Minio | None = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Ensure the MinIO client is initialized and bucket exists."""
        if self._initialized:
            return

        try:
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )

            # Ensure bucket exists
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.debug(f"Bucket already exists: {self.bucket_name}")

            self._initialized = True
            logger.info(f"MinIO storage service initialized: {self.endpoint}")

        except S3Error as e:
            logger.error(f"Failed to initialize MinIO: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing MinIO: {e}")
            raise

    def _build_path(self, case_id: str, filename: str) -> str:
        """
        Build the storage path for a file.

        Args:
            case_id: Case ID (e.g., 'FIN-USB-0001')
            filename: Original filename

        Returns:
            Path in format: cases/{case_id}/{filename}
        """
        # Sanitize filename to prevent path traversal
        safe_filename = os.path.basename(filename)
        return f"cases/{case_id}/{safe_filename}"

    async def upload_file(
        self,
        case_id: str,
        file: BinaryIO | bytes,
        filename: str,
        content_type: str | None = None,
    ) -> str:
        """
        Upload a file to MinIO storage.

        Args:
            case_id: Case ID for the file
            file: File object or bytes to upload
            filename: Original filename
            content_type: MIME type (optional)

        Returns:
            Storage path of the uploaded file

        Raises:
            S3Error: If upload fails
        """
        await self._ensure_initialized()

        try:
            path = self._build_path(case_id, filename)

            # Convert bytes to BytesIO if necessary
            if isinstance(file, bytes):
                file_data = BytesIO(file)
                file_size = len(file)
            else:
                # Get file size
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Seek back to start
                file_data = file

            # Upload to MinIO
            self.client.put_object(
                self.bucket_name,
                path,
                file_data,
                file_size,
                content_type=content_type or "application/octet-stream",
            )

            logger.info(f"Uploaded file: {path} ({file_size} bytes)")
            return path

        except S3Error as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading file {filename}: {e}")
            raise

    async def download_file(self, path: str) -> bytes:
        """
        Download a file from MinIO storage.

        Args:
            path: Storage path of the file

        Returns:
            File contents as bytes

        Raises:
            S3Error: If download fails or file not found
        """
        await self._ensure_initialized()

        try:
            response = self.client.get_object(self.bucket_name, path)
            data = response.read()
            response.close()
            response.release_conn()

            logger.info(f"Downloaded file: {path} ({len(data)} bytes)")
            return data

        except S3Error as e:
            logger.error(f"Failed to download file {path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading file {path}: {e}")
            raise

    async def delete_file(self, path: str) -> bool:
        """
        Delete a file from MinIO storage.

        Args:
            path: Storage path of the file

        Returns:
            True if deleted successfully

        Raises:
            S3Error: If deletion fails
        """
        await self._ensure_initialized()

        try:
            self.client.remove_object(self.bucket_name, path)
            logger.info(f"Deleted file: {path}")
            return True

        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"File not found for deletion: {path}")
                return False
            logger.error(f"Failed to delete file {path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting file {path}: {e}")
            raise

    async def generate_presigned_url(
        self,
        path: str,
        expires: int = 3600,
    ) -> str:
        """
        Generate a presigned URL for temporary file access.

        Args:
            path: Storage path of the file
            expires: URL expiration time in seconds (default: 3600 = 1 hour)

        Returns:
            Presigned URL string

        Raises:
            S3Error: If URL generation fails
        """
        await self._ensure_initialized()

        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                path,
                expires=timedelta(seconds=expires),
            )

            logger.debug(f"Generated presigned URL for: {path} (expires in {expires}s)")
            return url

        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL for {path}: {e}")
            raise

    async def file_exists(self, path: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            path: Storage path of the file

        Returns:
            True if file exists, False otherwise
        """
        await self._ensure_initialized()

        try:
            self.client.stat_object(self.bucket_name, path)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise

    async def list_files(self, prefix: str = "") -> list[dict]:
        """
        List files in storage with optional prefix filter.

        Args:
            prefix: Path prefix to filter (e.g., 'cases/FIN-USB-0001/')

        Returns:
            List of file info dictionaries
        """
        await self._ensure_initialized()

        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True,
            )

            files = []
            for obj in objects:
                files.append({
                    "path": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                })

            return files

        except S3Error as e:
            logger.error(f"Failed to list files with prefix {prefix}: {e}")
            raise


# Singleton instance
storage_service = StorageService()
