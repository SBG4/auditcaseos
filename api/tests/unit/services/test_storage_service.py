"""
Unit tests for StorageService.

Tests cover:
- File upload with mocked MinIO
- File download
- File deletion
- Presigned URL generation
- File existence checks
- Path building logic

Source: pytest best practices
"""

import pytest
from io import BytesIO
from unittest.mock import MagicMock, patch

from minio.error import S3Error

from app.services.storage_service import StorageService


@pytest.mark.unit
class TestStorageServiceInit:
    """Tests for StorageService initialization."""

    def test_storage_service_default_init(self):
        """Test StorageService initializes with defaults."""
        with patch.dict('os.environ', {}, clear=True):
            service = StorageService()

            assert service.endpoint == "localhost:9000"
            assert service.access_key == "minioadmin"
            assert service.secret_key == "minioadmin"
            assert service.bucket_name == "auditcaseos"
            assert service.secure is False
            assert service.client is None
            assert service._initialized is False

    def test_storage_service_custom_init(self):
        """Test StorageService initializes with custom values."""
        service = StorageService(
            endpoint="custom:9000",
            access_key="custom_access",
            secret_key="custom_secret",
            bucket_name="custom_bucket",
            secure=True,
        )

        assert service.endpoint == "custom:9000"
        assert service.access_key == "custom_access"
        assert service.secret_key == "custom_secret"
        assert service.bucket_name == "custom_bucket"
        assert service.secure is True

    def test_storage_service_env_vars(self):
        """Test StorageService reads from environment variables."""
        env_vars = {
            "MINIO_ENDPOINT": "env-host:9000",
            "MINIO_ACCESS_KEY": "env_access",
            "MINIO_SECRET_KEY": "env_secret",
            "MINIO_BUCKET": "env_bucket",
            "MINIO_SECURE": "true",
        }
        with patch.dict('os.environ', env_vars):
            service = StorageService()

            assert service.endpoint == "env-host:9000"
            assert service.access_key == "env_access"
            assert service.secret_key == "env_secret"
            assert service.bucket_name == "env_bucket"
            assert service.secure is True


@pytest.mark.unit
class TestPathBuilding:
    """Tests for path building logic."""

    def test_build_path_simple(self):
        """Test simple path building."""
        service = StorageService()
        path = service._build_path("FIN-USB-0001", "document.pdf")

        assert path == "cases/FIN-USB-0001/document.pdf"

    def test_build_path_with_spaces(self):
        """Test path building with spaces in filename."""
        service = StorageService()
        path = service._build_path("IT-EMAIL-0001", "my document.pdf")

        assert path == "cases/IT-EMAIL-0001/my document.pdf"

    def test_build_path_prevents_traversal(self):
        """Test path building prevents directory traversal."""
        service = StorageService()
        path = service._build_path("HR-POLICY-0001", "../../../etc/passwd")

        # os.path.basename should strip the traversal attempt
        assert path == "cases/HR-POLICY-0001/passwd"

    def test_build_path_with_subdirectory(self):
        """Test path building strips subdirectories."""
        service = StorageService()
        path = service._build_path("SEC-ACCESS-0001", "subdir/file.txt")

        assert path == "cases/SEC-ACCESS-0001/file.txt"


@pytest.mark.unit
class TestUploadFile:
    """Tests for file upload."""

    @pytest.mark.asyncio
    async def test_upload_file_bytes(self, mock_minio_client):
        """Test uploading bytes data."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        file_content = b"test file content"
        path = await service.upload_file(
            case_id="FIN-USB-0001",
            file=file_content,
            filename="test.txt",
            content_type="text/plain",
        )

        assert path == "cases/FIN-USB-0001/test.txt"
        mock_minio_client.put_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_file_bytesio(self, mock_minio_client):
        """Test uploading BytesIO object."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        file_content = BytesIO(b"test file content")
        path = await service.upload_file(
            case_id="IT-EMAIL-0001",
            file=file_content,
            filename="document.pdf",
            content_type="application/pdf",
        )

        assert path == "cases/IT-EMAIL-0001/document.pdf"
        mock_minio_client.put_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_file_default_content_type(self, mock_minio_client):
        """Test upload uses default content type."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        path = await service.upload_file(
            case_id="HR-POLICY-0001",
            file=b"data",
            filename="unknown.xyz",
        )

        assert path == "cases/HR-POLICY-0001/unknown.xyz"
        # Verify content_type defaults to octet-stream
        call_args = mock_minio_client.put_object.call_args
        assert call_args.kwargs.get("content_type") == "application/octet-stream"


@pytest.mark.unit
class TestDownloadFile:
    """Tests for file download."""

    @pytest.mark.asyncio
    async def test_download_file_success(self, mock_minio_client):
        """Test successful file download."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        data = await service.download_file("cases/FIN-USB-0001/test.pdf")

        assert data == b"test file content"
        mock_minio_client.get_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, mock_minio_client):
        """Test download when file doesn't exist."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        # Mock S3Error for not found
        mock_minio_client.get_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Object not found",
            resource="/test",
            request_id="123",
            host_id="456",
            response=None,
        )

        with pytest.raises(S3Error) as exc_info:
            await service.download_file("cases/FIN-USB-0001/missing.pdf")

        assert exc_info.value.code == "NoSuchKey"


@pytest.mark.unit
class TestDeleteFile:
    """Tests for file deletion."""

    @pytest.mark.asyncio
    async def test_delete_file_success(self, mock_minio_client):
        """Test successful file deletion."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        result = await service.delete_file("cases/FIN-USB-0001/test.pdf")

        assert result is True
        mock_minio_client.remove_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, mock_minio_client):
        """Test deletion when file doesn't exist."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        # Mock S3Error for not found
        mock_minio_client.remove_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Object not found",
            resource="/test",
            request_id="123",
            host_id="456",
            response=None,
        )

        result = await service.delete_file("cases/FIN-USB-0001/missing.pdf")

        assert result is False


@pytest.mark.unit
class TestFileExists:
    """Tests for file existence checks."""

    @pytest.mark.asyncio
    async def test_file_exists_true(self, mock_minio_client):
        """Test file exists returns true."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        result = await service.file_exists("cases/FIN-USB-0001/test.pdf")

        assert result is True
        mock_minio_client.stat_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_exists_false(self, mock_minio_client):
        """Test file exists returns false when not found."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        mock_minio_client.stat_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Object not found",
            resource="/test",
            request_id="123",
            host_id="456",
            response=None,
        )

        result = await service.file_exists("cases/FIN-USB-0001/missing.pdf")

        assert result is False


@pytest.mark.unit
class TestPresignedUrl:
    """Tests for presigned URL generation."""

    @pytest.mark.asyncio
    async def test_generate_presigned_url(self, mock_minio_client):
        """Test presigned URL generation."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        mock_minio_client.presigned_get_object.return_value = (
            "http://minio:9000/auditcaseos/cases/FIN-USB-0001/test.pdf?signature=xyz"
        )

        url = await service.generate_presigned_url(
            "cases/FIN-USB-0001/test.pdf",
            expires=7200,
        )

        assert "test.pdf" in url
        mock_minio_client.presigned_get_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_presigned_url_default_expiry(self, mock_minio_client):
        """Test presigned URL with default expiry."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        mock_minio_client.presigned_get_object.return_value = "http://example.com/signed"

        await service.generate_presigned_url("cases/FIN-USB-0001/test.pdf")

        # Check that default 3600 seconds was used
        call_args = mock_minio_client.presigned_get_object.call_args
        from datetime import timedelta
        assert call_args.kwargs.get("expires") == timedelta(seconds=3600)


@pytest.mark.unit
class TestListFiles:
    """Tests for file listing."""

    @pytest.mark.asyncio
    async def test_list_files_empty(self, mock_minio_client):
        """Test listing files when none exist."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        mock_minio_client.list_objects.return_value = []

        files = await service.list_files("cases/FIN-USB-0001/")

        assert files == []

    @pytest.mark.asyncio
    async def test_list_files_with_results(self, mock_minio_client):
        """Test listing files with results."""
        service = StorageService()
        service.client = mock_minio_client
        service._initialized = True

        # Create mock object list
        mock_obj = MagicMock()
        mock_obj.object_name = "cases/FIN-USB-0001/test.pdf"
        mock_obj.size = 1024
        mock_obj.last_modified = "2024-01-01T00:00:00Z"
        mock_obj.etag = "abc123"

        mock_minio_client.list_objects.return_value = [mock_obj]

        files = await service.list_files("cases/FIN-USB-0001/")

        assert len(files) == 1
        assert files[0]["path"] == "cases/FIN-USB-0001/test.pdf"
        assert files[0]["size"] == 1024
