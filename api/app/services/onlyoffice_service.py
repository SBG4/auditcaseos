"""ONLYOFFICE service for document editing integration."""

import logging
import re
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OnlyOfficeService:
    """Service for interacting with ONLYOFFICE Document Server."""

    def __init__(self):
        """Initialize ONLYOFFICE service with configuration."""
        self.external_url = settings.onlyoffice_url  # For browser access
        self.internal_url = settings.onlyoffice_internal_url  # For server-to-server
        self.jwt_secret = settings.onlyoffice_jwt_secret
        self.nextcloud_internal_url = settings.nextcloud_url  # Internal Nextcloud URL
        self.nextcloud_external_url = "http://localhost:18081"  # External Nextcloud URL
        self.nextcloud_user = settings.nextcloud_admin_user
        self.nextcloud_pass = settings.nextcloud_admin_password

    async def health_check(self) -> dict[str, Any]:
        """
        Check ONLYOFFICE Document Server connection status.

        Returns:
            Dict with status and details
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check healthcheck endpoint
                response = await client.get(f"{self.internal_url}/healthcheck")
                if response.status_code == 200:
                    # Also check if document server is ready
                    info_response = await client.get(f"{self.internal_url}/info/info.json")
                    if info_response.status_code == 200:
                        info = info_response.json()
                        return {
                            "available": True,
                            "version": info.get("version", "unknown"),
                            "build": info.get("build", "unknown"),
                            "external_url": self.external_url,
                        }
                    return {
                        "available": True,
                        "version": "unknown",
                        "external_url": self.external_url,
                    }
                return {"available": False, "error": f"Status code: {response.status_code}"}
        except Exception as e:
            logger.warning(f"ONLYOFFICE health check failed: {e}")
            return {"available": False, "error": str(e)}

    def get_editor_url(self) -> str:
        """Get the ONLYOFFICE editor URL for browser access."""
        return self.external_url

    async def get_nextcloud_file_id(self, file_path: str) -> int | None:
        """
        Get the Nextcloud file ID for a file path using WebDAV PROPFIND.

        Args:
            file_path: Path to the file in Nextcloud (e.g., "AuditCases/IT-POLICY-0001/Reports/report.docx")

        Returns:
            The Nextcloud file ID or None if not found
        """
        try:
            webdav_url = f"{self.nextcloud_internal_url}/remote.php/dav/files/{self.nextcloud_user}/{file_path}"
            propfind_body = """<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
  <d:prop>
    <oc:fileid/>
  </d:prop>
</d:propfind>"""

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    "PROPFIND",
                    webdav_url,
                    content=propfind_body,
                    headers={
                        "Content-Type": "application/xml",
                        "Depth": "0",
                    },
                    auth=(self.nextcloud_user, self.nextcloud_pass),
                )
                if response.status_code in [200, 207]:
                    # Parse file ID from response
                    match = re.search(r'<oc:fileid>(\d+)</oc:fileid>', response.text)
                    if match:
                        return int(match.group(1))
                logger.warning(f"Could not get file ID for {file_path}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting file ID from Nextcloud: {e}")
            return None

    def get_nextcloud_edit_url(self, file_path: str, file_id: int | None = None) -> str:
        """
        Generate a Nextcloud ONLYOFFICE edit URL for a file.

        Args:
            file_path: Path to the file in Nextcloud (e.g., "AuditCases/IT-POLICY-0001/Reports/report.docx")
            file_id: Optional Nextcloud file ID. If provided, uses direct ONLYOFFICE URL.

        Returns:
            URL to edit the document in Nextcloud with ONLYOFFICE
        """
        if file_id:
            # Direct ONLYOFFICE URL with file ID
            return f"{self.nextcloud_external_url}/index.php/apps/onlyoffice/{file_id}"
        else:
            # Fallback to file browser URL
            import urllib.parse
            encoded_path = urllib.parse.quote(f"/{file_path}", safe='/')
            dir_path = "/".join(file_path.split("/")[:-1])
            encoded_dir = urllib.parse.quote(f"/{dir_path}", safe='/')
            return f"{self.nextcloud_external_url}/index.php/apps/files/?dir={encoded_dir}"

    def get_supported_extensions(self) -> dict[str, list[str]]:
        """
        Get supported file extensions for ONLYOFFICE editing.

        Returns:
            Dict with categories and their supported extensions
        """
        return {
            "documents": [".docx", ".doc", ".odt", ".txt", ".rtf", ".html", ".htm", ".epub", ".pdf"],
            "spreadsheets": [".xlsx", ".xls", ".ods", ".csv"],
            "presentations": [".pptx", ".ppt", ".odp"],
            "editable": [".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp"],  # Fully editable formats
        }

    def is_editable(self, filename: str) -> bool:
        """
        Check if a file can be edited in ONLYOFFICE.

        Args:
            filename: The filename to check

        Returns:
            True if the file can be edited
        """
        extensions = self.get_supported_extensions()
        editable_exts = extensions["editable"]
        lower_filename = filename.lower()
        return any(lower_filename.endswith(ext) for ext in editable_exts)

    def is_viewable(self, filename: str) -> bool:
        """
        Check if a file can be viewed in ONLYOFFICE.

        Args:
            filename: The filename to check

        Returns:
            True if the file can be viewed
        """
        extensions = self.get_supported_extensions()
        all_viewable = (
            extensions["documents"] +
            extensions["spreadsheets"] +
            extensions["presentations"]
        )
        lower_filename = filename.lower()
        return any(lower_filename.endswith(ext) for ext in all_viewable)

    def get_document_type(self, filename: str) -> str | None:
        """
        Get the ONLYOFFICE document type for a file.

        Args:
            filename: The filename to check

        Returns:
            Document type ('word', 'cell', 'slide') or None
        """
        extensions = self.get_supported_extensions()
        lower_filename = filename.lower()

        for ext in extensions["documents"]:
            if lower_filename.endswith(ext):
                return "word"

        for ext in extensions["spreadsheets"]:
            if lower_filename.endswith(ext):
                return "cell"

        for ext in extensions["presentations"]:
            if lower_filename.endswith(ext):
                return "slide"

        return None


# Singleton instance
onlyoffice_service = OnlyOfficeService()
