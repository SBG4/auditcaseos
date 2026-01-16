"""
Paperless-ngx service for OCR and document processing.

This service integrates with Paperless-ngx to:
- Upload documents for OCR processing
- Retrieve extracted text from processed documents
- Search documents by content
- Manage document tags for case organization
"""

import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class PaperlessService:
    """Service for interacting with Paperless-ngx API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout: float = 60.0,
    ):
        """
        Initialize the PaperlessService.

        Args:
            base_url: Paperless-ngx base URL (default from env: PAPERLESS_URL)
            api_token: API token for authentication (default from env: PAPERLESS_API_TOKEN)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or os.getenv("PAPERLESS_URL", "http://localhost:18080")).rstrip("/")
        self.api_token = api_token or os.getenv("PAPERLESS_API_TOKEN", "")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        """Check if the service is properly configured with an API token."""
        return bool(self.api_token)

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Accept": "application/json",
        }
        if self.api_token:
            headers["Authorization"] = f"Token {self.api_token}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> dict[str, Any]:
        """
        Check if Paperless-ngx is accessible and healthy.

        Returns:
            dict with status and version info

        Raises:
            httpx.HTTPError: If the health check fails
        """
        try:
            # Create a client that follows redirects for health check
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=10.0,
                follow_redirects=True,
            ) as client:
                # Try to access a simple endpoint - the login page is always accessible
                response = await client.get("/")
                # 200 or 302 both indicate Paperless is running
                if response.status_code in (200, 302):
                    return {
                        "status": "healthy",
                        "base_url": self.base_url,
                        "configured": self.is_configured,
                    }
                return {
                    "status": "degraded",
                    "base_url": self.base_url,
                    "configured": self.is_configured,
                    "http_status": response.status_code,
                }
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Paperless: {e}")
            return {
                "status": "unreachable",
                "base_url": self.base_url,
                "error": "Cannot connect to Paperless server",
            }
        except httpx.HTTPError as e:
            logger.error(f"Paperless health check failed: {e}")
            return {
                "status": "unhealthy",
                "base_url": self.base_url,
                "error": str(e),
            }

    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        title: str | None = None,
        correspondent: str | None = None,
        tags: list[int] | None = None,
        case_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload a document to Paperless for OCR processing.

        Args:
            file_content: Binary content of the file
            filename: Original filename
            title: Document title (defaults to filename)
            correspondent: Correspondent name (optional)
            tags: List of tag IDs to apply (optional)
            case_id: Case ID to use as tag/title prefix (optional)

        Returns:
            dict with task_id for tracking the upload

        Raises:
            httpx.HTTPError: If the upload fails
        """
        if not self.is_configured:
            raise ValueError("Paperless API token not configured. Set PAPERLESS_API_TOKEN environment variable.")

        client = await self._get_client()

        # Prepare the multipart form data
        # Paperless expects the file in a field named 'document'
        files = {
            "document": (filename, file_content, "application/octet-stream"),
        }

        data: dict[str, Any] = {}
        if title or case_id:
            data["title"] = f"[{case_id}] {title or filename}" if case_id else (title or filename)
        if correspondent:
            data["correspondent"] = correspondent
        if tags:
            # Tags need to be sent as comma-separated IDs
            data["tags"] = ",".join(str(t) for t in tags)

        try:
            # Use a longer timeout for file uploads
            response = await client.post(
                "/api/documents/post_document/",
                files=files,
                data=data,
                timeout=120.0,
            )
            response.raise_for_status()

            # Paperless returns a task ID for async processing
            result = response.json() if response.text else {"status": "accepted"}
            logger.info(f"Document uploaded to Paperless: {filename} -> {result}")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to upload document to Paperless: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error uploading document: {e}")
            raise

    async def get_document(self, document_id: int) -> dict[str, Any]:
        """
        Get a document by ID, including its OCR text.

        Args:
            document_id: Paperless document ID

        Returns:
            dict with document metadata and content

        Raises:
            httpx.HTTPError: If the request fails
        """
        if not self.is_configured:
            raise ValueError("Paperless API token not configured")

        client = await self._get_client()

        try:
            response = await client.get(f"/api/documents/{document_id}/")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Document not found in Paperless: {document_id}")
                return {}
            logger.error(f"Failed to get document from Paperless: {e}")
            raise

    async def get_document_content(self, document_id: int) -> str:
        """
        Get the extracted text content of a document.

        Args:
            document_id: Paperless document ID

        Returns:
            Extracted text content

        Raises:
            httpx.HTTPError: If the request fails
        """
        doc = await self.get_document(document_id)
        return doc.get("content", "")

    async def search_documents(
        self,
        query: str,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        """
        Search documents by content or metadata.

        Args:
            query: Search query string
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            dict with results, count, and pagination info

        Raises:
            httpx.HTTPError: If the search fails
        """
        if not self.is_configured:
            raise ValueError("Paperless API token not configured")

        client = await self._get_client()

        try:
            response = await client.get(
                "/api/documents/",
                params={
                    "query": query,
                    "page": page,
                    "page_size": page_size,
                },
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to search Paperless documents: {e}")
            raise

    async def list_documents(
        self,
        page: int = 1,
        page_size: int = 25,
        ordering: str = "-created",
    ) -> dict[str, Any]:
        """
        List all documents with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of results per page
            ordering: Field to order by (prefix with - for descending)

        Returns:
            dict with results, count, and pagination info
        """
        if not self.is_configured:
            raise ValueError("Paperless API token not configured")

        client = await self._get_client()

        try:
            response = await client.get(
                "/api/documents/",
                params={
                    "page": page,
                    "page_size": page_size,
                    "ordering": ordering,
                },
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to list Paperless documents: {e}")
            raise

    async def get_or_create_tag(self, name: str) -> int:
        """
        Get or create a tag by name.

        Args:
            name: Tag name (e.g., case ID)

        Returns:
            Tag ID

        Raises:
            httpx.HTTPError: If the operation fails
        """
        if not self.is_configured:
            raise ValueError("Paperless API token not configured")

        client = await self._get_client()

        try:
            # First, search for existing tag
            response = await client.get(
                "/api/tags/",
                params={"name__iexact": name},
            )
            response.raise_for_status()
            data = response.json()

            if data.get("results"):
                return data["results"][0]["id"]

            # Tag doesn't exist, create it
            create_response = await client.post(
                "/api/tags/",
                json={"name": name},
            )
            create_response.raise_for_status()
            return create_response.json()["id"]

        except httpx.HTTPError as e:
            logger.error(f"Failed to get/create tag '{name}': {e}")
            raise

    async def get_documents_by_tag(
        self,
        tag_id: int,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """
        Get all documents with a specific tag.

        Args:
            tag_id: Tag ID to filter by
            page: Page number
            page_size: Results per page

        Returns:
            dict with results and pagination info
        """
        if not self.is_configured:
            raise ValueError("Paperless API token not configured")

        client = await self._get_client()

        try:
            response = await client.get(
                "/api/documents/",
                params={
                    "tags__id": tag_id,
                    "page": page,
                    "page_size": page_size,
                },
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get documents by tag {tag_id}: {e}")
            raise

    async def wait_for_document(
        self,
        task_id: str,
        max_wait: int = 300,
        poll_interval: int = 5,
    ) -> dict[str, Any] | None:
        """
        Wait for a document upload task to complete.

        Args:
            task_id: Task ID from upload_document
            max_wait: Maximum time to wait in seconds
            poll_interval: Time between status checks in seconds

        Returns:
            Document info if successful, None if timed out
        """
        if not self.is_configured:
            raise ValueError("Paperless API token not configured")

        client = await self._get_client()
        elapsed = 0

        while elapsed < max_wait:
            try:
                response = await client.get(f"/api/tasks/?task_id={task_id}")
                response.raise_for_status()
                tasks = response.json()

                if tasks.get("results"):
                    task = tasks["results"][0]
                    status = task.get("status")

                    if status == "SUCCESS":
                        # Get the document ID from the task result
                        result = task.get("result")
                        if result and isinstance(result, int):
                            return await self.get_document(result)
                        return task

                    elif status in ("FAILURE", "REVOKED"):
                        logger.error(f"Document processing failed: {task}")
                        return None

                # Task still pending/processing
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            except httpx.HTTPError as e:
                logger.warning(f"Error checking task status: {e}")
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

        logger.warning(f"Timed out waiting for document task {task_id}")
        return None

    async def download_document(self, document_id: int) -> bytes:
        """
        Download the original document file.

        Args:
            document_id: Paperless document ID

        Returns:
            Original file content as bytes
        """
        if not self.is_configured:
            raise ValueError("Paperless API token not configured")

        client = await self._get_client()

        try:
            response = await client.get(
                f"/api/documents/{document_id}/download/",
                timeout=120.0,
            )
            response.raise_for_status()
            return response.content

        except httpx.HTTPError as e:
            logger.error(f"Failed to download document {document_id}: {e}")
            raise


# Singleton instance
paperless_service = PaperlessService()
