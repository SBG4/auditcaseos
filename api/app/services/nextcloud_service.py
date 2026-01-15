"""Nextcloud service for file collaboration and case folder management."""

import logging
from typing import Any
from xml.etree import ElementTree

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class NextcloudService:
    """Service for interacting with Nextcloud via WebDAV and OCS API."""

    def __init__(self):
        """Initialize Nextcloud service with configuration."""
        self.base_url = settings.nextcloud_url
        self.username = settings.nextcloud_admin_user
        self.password = settings.nextcloud_admin_password
        self.webdav_url = f"{self.base_url}/remote.php/dav/files/{self.username}"
        self.ocs_url = f"{self.base_url}/ocs/v2.php"

    def _get_auth(self) -> tuple[str, str]:
        """Get authentication tuple."""
        return (self.username, self.password)

    async def health_check(self) -> dict[str, Any]:
        """
        Check Nextcloud connection status.

        Returns:
            Dict with status and details
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/status.php",
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "available": True,
                        "installed": data.get("installed", False),
                        "version": data.get("versionstring", "unknown"),
                        "maintenance": data.get("maintenance", False),
                    }
                return {"available": False, "error": f"Status code: {response.status_code}"}
        except Exception as e:
            logger.error(f"Nextcloud health check failed: {e}")
            return {"available": False, "error": str(e)}

    async def create_folder(self, path: str) -> bool:
        """
        Create a folder in Nextcloud.

        Args:
            path: Folder path relative to user's root (e.g., "AuditCases/FIN-USB-0001")

        Returns:
            True if folder was created or already exists
        """
        try:
            # Ensure path doesn't start with /
            path = path.lstrip("/")
            url = f"{self.webdav_url}/{path}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use MKCOL method to create directory
                response = await client.request(
                    method="MKCOL",
                    url=url,
                    auth=self._get_auth(),
                )

                if response.status_code in [201, 405]:  # 201 = Created, 405 = Already exists
                    logger.info(f"Folder created/exists: {path}")
                    return True
                else:
                    logger.error(f"Failed to create folder {path}: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Error creating folder {path}: {e}")
            return False

    async def create_case_folder(self, case_id: str) -> dict[str, Any]:
        """
        Create folder structure for a case.

        Creates:
        - AuditCases/{case_id}/
        - AuditCases/{case_id}/Evidence/
        - AuditCases/{case_id}/Reports/
        - AuditCases/{case_id}/Notes/

        Args:
            case_id: The case ID (e.g., "FIN-USB-0001")

        Returns:
            Dict with creation status
        """
        base_path = f"AuditCases/{case_id}"
        subfolders = ["Evidence", "Reports", "Notes"]

        results = {"case_id": case_id, "folders_created": []}

        # Create base AuditCases folder first
        await self.create_folder("AuditCases")

        # Create case folder
        if await self.create_folder(base_path):
            results["folders_created"].append(base_path)

            # Create subfolders
            for subfolder in subfolders:
                folder_path = f"{base_path}/{subfolder}"
                if await self.create_folder(folder_path):
                    results["folders_created"].append(folder_path)

        results["success"] = len(results["folders_created"]) > 0
        return results

    async def upload_file(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> bool:
        """
        Upload a file to Nextcloud.

        Args:
            path: File path relative to user's root
            content: File content as bytes
            content_type: MIME type of the file

        Returns:
            True if upload was successful
        """
        try:
            path = path.lstrip("/")
            url = f"{self.webdav_url}/{path}"

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.put(
                    url,
                    content=content,
                    auth=self._get_auth(),
                    headers={"Content-Type": content_type},
                )

                if response.status_code in [201, 204]:  # 201 = Created, 204 = Updated
                    logger.info(f"File uploaded: {path}")
                    return True
                else:
                    logger.error(f"Failed to upload {path}: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Error uploading file {path}: {e}")
            return False

    async def list_folder(self, path: str = "") -> list[dict[str, Any]]:
        """
        List contents of a folder.

        Args:
            path: Folder path relative to user's root

        Returns:
            List of file/folder information
        """
        try:
            path = path.lstrip("/")
            url = f"{self.webdav_url}/{path}" if path else self.webdav_url

            # PROPFIND request body
            propfind_body = """<?xml version="1.0" encoding="utf-8" ?>
            <d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
                <d:prop>
                    <d:displayname/>
                    <d:getcontenttype/>
                    <d:getcontentlength/>
                    <d:getlastmodified/>
                    <d:resourcetype/>
                    <oc:fileid/>
                </d:prop>
            </d:propfind>"""

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method="PROPFIND",
                    url=url,
                    content=propfind_body.encode(),
                    auth=self._get_auth(),
                    headers={
                        "Content-Type": "application/xml",
                        "Depth": "1",
                    },
                )

                if response.status_code == 207:  # Multi-Status
                    return self._parse_propfind_response(response.text, path)
                else:
                    logger.error(f"Failed to list folder {path}: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Error listing folder {path}: {e}")
            return []

    def _parse_propfind_response(self, xml_text: str, base_path: str) -> list[dict[str, Any]]:
        """Parse WebDAV PROPFIND response."""
        items = []

        try:
            # Define namespaces
            namespaces = {
                "d": "DAV:",
                "oc": "http://owncloud.org/ns",
            }

            root = ElementTree.fromstring(xml_text)

            for response in root.findall(".//d:response", namespaces):
                href = response.find("d:href", namespaces)
                if href is None:
                    continue

                # Extract path from href
                path = href.text or ""
                # Skip the parent directory itself
                if path.rstrip("/").endswith(base_path.rstrip("/")):
                    continue

                propstat = response.find("d:propstat", namespaces)
                if propstat is None:
                    continue

                prop = propstat.find("d:prop", namespaces)
                if prop is None:
                    continue

                # Check if it's a collection (directory)
                resourcetype = prop.find("d:resourcetype", namespaces)
                is_directory = resourcetype is not None and resourcetype.find("d:collection", namespaces) is not None

                displayname = prop.find("d:displayname", namespaces)
                contenttype = prop.find("d:getcontenttype", namespaces)
                contentlength = prop.find("d:getcontentlength", namespaces)
                lastmodified = prop.find("d:getlastmodified", namespaces)
                fileid = prop.find("oc:fileid", namespaces)

                item = {
                    "name": displayname.text if displayname is not None else path.split("/")[-1],
                    "path": path,
                    "is_directory": is_directory,
                    "content_type": contenttype.text if contenttype is not None else None,
                    "size": int(contentlength.text) if contentlength is not None and contentlength.text else 0,
                    "last_modified": lastmodified.text if lastmodified is not None else None,
                    "file_id": fileid.text if fileid is not None else None,
                }
                items.append(item)

        except Exception as e:
            logger.error(f"Error parsing PROPFIND response: {e}")

        return items

    async def download_file(self, path: str) -> bytes | None:
        """
        Download a file from Nextcloud.

        Args:
            path: File path relative to user's root

        Returns:
            File content as bytes or None if failed
        """
        try:
            path = path.lstrip("/")
            url = f"{self.webdav_url}/{path}"

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    url,
                    auth=self._get_auth(),
                )

                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"Failed to download {path}: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error downloading file {path}: {e}")
            return None

    async def delete_item(self, path: str) -> bool:
        """
        Delete a file or folder from Nextcloud.

        Args:
            path: Path relative to user's root

        Returns:
            True if deletion was successful
        """
        try:
            path = path.lstrip("/")
            url = f"{self.webdav_url}/{path}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    url,
                    auth=self._get_auth(),
                )

                if response.status_code in [204, 404]:  # 204 = Deleted, 404 = Not found (already deleted)
                    logger.info(f"Item deleted: {path}")
                    return True
                else:
                    logger.error(f"Failed to delete {path}: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Error deleting item {path}: {e}")
            return False

    async def get_share_link(self, path: str, password: str | None = None) -> dict[str, Any] | None:
        """
        Create a public share link for a file or folder.

        Args:
            path: Path relative to user's root
            password: Optional password for the share

        Returns:
            Share information dict or None if failed
        """
        try:
            path = path.lstrip("/")
            url = f"{self.ocs_url}/apps/files_sharing/api/v1/shares"

            data = {
                "path": f"/{path}",
                "shareType": 3,  # Public link
                "permissions": 1,  # Read only
            }
            if password:
                data["password"] = password

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    data=data,
                    auth=self._get_auth(),
                    headers={"OCS-APIRequest": "true"},
                )

                if response.status_code == 200:
                    # Parse OCS response
                    root = ElementTree.fromstring(response.text)
                    status = root.find(".//statuscode")
                    if status is not None and status.text == "100":
                        share_data = root.find(".//data")
                        if share_data is not None:
                            share_url = share_data.find("url")
                            share_id = share_data.find("id")
                            return {
                                "id": share_id.text if share_id is not None else None,
                                "url": share_url.text if share_url is not None else None,
                                "path": path,
                            }
                    logger.error(f"Failed to create share: {response.text}")
                    return None
                else:
                    logger.error(f"Failed to create share for {path}: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error creating share for {path}: {e}")
            return None

    async def get_case_folder_url(self, case_id: str) -> str:
        """
        Get the Nextcloud web URL for a case folder.

        Args:
            case_id: The case ID

        Returns:
            URL to the case folder in Nextcloud web interface
        """
        # External URL for browser access
        external_url = settings.nextcloud_url.replace("http://nextcloud", "http://localhost:18081")
        return f"{external_url}/apps/files/?dir=/AuditCases/{case_id}"


# Singleton instance
nextcloud_service = NextcloudService()
