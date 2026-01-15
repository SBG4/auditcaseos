"""Authentication service for user management and token handling."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.security import hash_password, verify_password, create_access_token

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""

    async def get_user_by_username(
        self,
        db: AsyncSession,
        username: str,
    ) -> dict[str, Any] | None:
        """
        Get a user by username.

        Args:
            db: Database session
            username: Username to look up

        Returns:
            User dict or None if not found
        """
        try:
            query = text("""
                SELECT id, username, email, password_hash, full_name, role, department, is_active, created_at
                FROM users
                WHERE username = :username
            """)
            result = await db.execute(query, {"username": username})
            row = result.fetchone()

            if row:
                return dict(row._mapping)
            return None

        except Exception as e:
            logger.error(f"Failed to get user by username: {e}")
            raise

    async def get_user_by_email(
        self,
        db: AsyncSession,
        email: str,
    ) -> dict[str, Any] | None:
        """
        Get a user by email.

        Args:
            db: Database session
            email: Email to look up

        Returns:
            User dict or None if not found
        """
        try:
            query = text("""
                SELECT id, username, email, password_hash, full_name, role, department, is_active, created_at
                FROM users
                WHERE email = :email
            """)
            result = await db.execute(query, {"email": email})
            row = result.fetchone()

            if row:
                return dict(row._mapping)
            return None

        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            raise

    async def get_user_by_id(
        self,
        db: AsyncSession,
        user_id: UUID | str,
    ) -> dict[str, Any] | None:
        """
        Get a user by ID.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            User dict or None if not found
        """
        try:
            query = text("""
                SELECT id, username, email, password_hash, full_name, role, department, is_active, created_at
                FROM users
                WHERE id = :user_id
            """)
            result = await db.execute(query, {"user_id": str(user_id)})
            row = result.fetchone()

            if row:
                return dict(row._mapping)
            return None

        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            raise

    async def authenticate_user(
        self,
        db: AsyncSession,
        username: str,
        password: str,
    ) -> dict[str, Any] | None:
        """
        Authenticate a user with username and password.

        Args:
            db: Database session
            username: Username or email
            password: Plain text password

        Returns:
            User dict if authenticated, None otherwise
        """
        # Try username first, then email
        user = await self.get_user_by_username(db, username)
        if not user:
            user = await self.get_user_by_email(db, username)

        if not user:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return None

        if not user.get("is_active", False):
            logger.warning(f"Authentication failed: user '{username}' is inactive")
            return None

        if not verify_password(password, user["password_hash"]):
            logger.warning(f"Authentication failed: invalid password for '{username}'")
            return None

        logger.info(f"User '{username}' authenticated successfully")
        return user

    async def create_user(
        self,
        db: AsyncSession,
        username: str,
        email: str,
        password: str,
        full_name: str,
        role: str = "viewer",
        department: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new user.

        Args:
            db: Database session
            username: Unique username
            email: Unique email address
            password: Plain text password (will be hashed)
            full_name: User's full name
            role: User role (admin, auditor, reviewer, viewer)
            department: Optional department

        Returns:
            Created user dict

        Raises:
            ValueError: If username or email already exists
        """
        try:
            # Check if username exists
            existing = await self.get_user_by_username(db, username)
            if existing:
                raise ValueError(f"Username '{username}' already exists")

            # Check if email exists
            existing = await self.get_user_by_email(db, email)
            if existing:
                raise ValueError(f"Email '{email}' already exists")

            # Hash password
            password_hash = hash_password(password)

            # Insert user
            query = text("""
                INSERT INTO users (username, email, password_hash, full_name, role, department)
                VALUES (:username, :email, :password_hash, :full_name, CAST(:role AS user_role), :department)
                RETURNING id, username, email, full_name, role, department, is_active, created_at
            """)

            result = await db.execute(query, {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "role": role,
                "department": department,
            })
            await db.commit()

            row = result.fetchone()
            user = dict(row._mapping) if row else {}

            logger.info(f"Created user: {username}")
            return user

        except ValueError:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create user: {e}")
            raise

    async def update_password(
        self,
        db: AsyncSession,
        user_id: UUID | str,
        new_password: str,
    ) -> bool:
        """
        Update a user's password.

        Args:
            db: Database session
            user_id: User UUID
            new_password: New plain text password

        Returns:
            True if updated successfully
        """
        try:
            password_hash = hash_password(new_password)

            query = text("""
                UPDATE users
                SET password_hash = :password_hash, updated_at = CURRENT_TIMESTAMP
                WHERE id = :user_id
                RETURNING id
            """)

            result = await db.execute(query, {
                "user_id": str(user_id),
                "password_hash": password_hash,
            })
            await db.commit()

            row = result.fetchone()
            if row:
                logger.info(f"Password updated for user {user_id}")
                return True
            return False

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update password: {e}")
            raise

    def create_user_token(self, user: dict[str, Any]) -> str:
        """
        Create JWT access token for a user.

        Args:
            user: User dict from database

        Returns:
            JWT access token string
        """
        token_data = {
            "sub": str(user["id"]),
            "email": user["email"],
            "role": str(user["role"]),
        }
        return create_access_token(token_data)

    async def list_users(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        List all users (admin only).

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of user dicts (without password_hash)
        """
        try:
            query = text("""
                SELECT id, username, email, full_name, role, department, is_active, created_at, updated_at
                FROM users
                ORDER BY created_at DESC
                OFFSET :skip LIMIT :limit
            """)

            result = await db.execute(query, {"skip": skip, "limit": limit})
            rows = result.fetchall()

            return [dict(row._mapping) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            raise

    async def update_user(
        self,
        db: AsyncSession,
        user_id: UUID | str,
        email: str | None = None,
        full_name: str | None = None,
        role: str | None = None,
        department: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any] | None:
        """
        Update a user's profile (admin only).

        Args:
            db: Database session
            user_id: User UUID
            email: New email (optional)
            full_name: New full name (optional)
            role: New role (optional)
            department: New department (optional)
            is_active: New active status (optional)

        Returns:
            Updated user dict or None if not found

        Raises:
            ValueError: If email already exists for another user
        """
        try:
            # Check if user exists
            existing = await self.get_user_by_id(db, user_id)
            if not existing:
                return None

            # If updating email, check uniqueness
            if email and email != existing["email"]:
                email_user = await self.get_user_by_email(db, email)
                if email_user and str(email_user["id"]) != str(user_id):
                    raise ValueError(f"Email '{email}' already exists")

            # Build dynamic update
            updates = []
            params: dict[str, Any] = {"user_id": str(user_id)}

            if email is not None:
                updates.append("email = :email")
                params["email"] = email
            if full_name is not None:
                updates.append("full_name = :full_name")
                params["full_name"] = full_name
            if role is not None:
                updates.append("role = CAST(:role AS user_role)")
                params["role"] = role
            if department is not None:
                updates.append("department = :department")
                params["department"] = department
            if is_active is not None:
                updates.append("is_active = :is_active")
                params["is_active"] = is_active

            if not updates:
                return existing

            updates.append("updated_at = CURRENT_TIMESTAMP")

            query = text(f"""
                UPDATE users
                SET {', '.join(updates)}
                WHERE id = :user_id
                RETURNING id, username, email, full_name, role, department, is_active, created_at, updated_at
            """)

            result = await db.execute(query, params)
            await db.commit()

            row = result.fetchone()
            if row:
                logger.info(f"Updated user {user_id}")
                return dict(row._mapping)
            return None

        except ValueError:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update user: {e}")
            raise

    async def deactivate_user(
        self,
        db: AsyncSession,
        user_id: UUID | str,
    ) -> bool:
        """
        Deactivate a user account (soft delete).

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            True if deactivated, False if user not found
        """
        try:
            query = text("""
                UPDATE users
                SET is_active = false, updated_at = CURRENT_TIMESTAMP
                WHERE id = :user_id
                RETURNING id
            """)

            result = await db.execute(query, {"user_id": str(user_id)})
            await db.commit()

            row = result.fetchone()
            if row:
                logger.info(f"Deactivated user {user_id}")
                return True
            return False

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to deactivate user: {e}")
            raise

    async def count_users(self, db: AsyncSession) -> int:
        """
        Count total users.

        Args:
            db: Database session

        Returns:
            Total user count
        """
        try:
            query = text("SELECT COUNT(*) FROM users")
            result = await db.execute(query)
            row = result.fetchone()
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"Failed to count users: {e}")
            raise


# Singleton instance
auth_service = AuthService()
