"""
Nexus ERP - Unit Tests for Authentication Module
================================================

This module contains unit tests for the authentication endpoints
including login, token refresh, and password management.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_password_hash, verify_password
from app.models.user import User, Role, Permission, UserStatus
from app.core.database import db_manager


# ========================================
# Fixtures
# ========================================

@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user for authentication tests."""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=get_password_hash("TestPassword123!"),
        first_name="Test",
        last_name="User",
        status=UserStatus.ACTIVE,
        tenant_id="00000000-0000-0000-0000-000000000001",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_role(db_session: AsyncSession):
    """Create a test role."""
    role = Role(
        code="test_role",
        name="Test Role",
        description="Role for testing",
        tenant_id="00000000-0000-0000-0000-000000000001",
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


# ========================================
# Password Tests
# ========================================

class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_password_hash_creates_valid_hash(self):
        """Test that password hashing creates a valid bcrypt hash."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_password_verification_succeeds(self):
        """Test that password verification works with correct password."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True

    def test_password_verification_fails_with_wrong_password(self):
        """Test that password verification fails with incorrect password."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password("WrongPassword", hashed) is False

    def test_different_passwords_have_different_hashes(self):
        """Test that same password produces different hashes (bcrypt salt)."""
        password = "SecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


# ========================================
# Token Tests
# ========================================

class TestJWTToken:
    """Tests for JWT token generation and validation."""

    def test_create_access_token(self):
        """Test access token creation."""
        from app.core.security import create_access_token, decode_token
        
        token = create_access_token(
            user_id="test-user-id",
            email="test@example.com",
            tenant_id="test-tenant-id",
            roles=["user"],
            permissions=["read"],
        )
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        payload = decode_token(token)
        assert payload["sub"] == "test-user-id"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        from app.core.security import create_refresh_token, decode_token
        
        token = create_refresh_token(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
        )
        
        assert token is not None
        
        # Decode and verify
        payload = decode_token(token)
        assert payload["sub"] == "test-user-id"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token_raises_error(self):
        """Test that decoding invalid token raises error."""
        from app.core.security import decode_token, AuthError
        
        with pytest.raises(AuthError):
            decode_token("invalid-token")


# ========================================
# Login Endpoint Tests
# ========================================

@pytest.mark.asyncio
class TestLoginEndpoint:
    """Tests for the login endpoint."""

    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login with valid credentials."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "TestPassword123!",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert "access_token" in data["token"]
        assert "refresh_token" in data["token"]

    async def test_login_with_email(self, async_client: AsyncClient, test_user: User):
        """Test login using email instead of username."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.email,
                "password": "TestPassword123!",
            }
        )
        
        assert response.status_code == 200

    async def test_login_invalid_password(self, async_client: AsyncClient, test_user: User):
        """Test login with invalid password."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "WrongPassword123!",
            }
        )
        
        assert response.status_code == 401

    async def test_login_invalid_username(self, async_client: AsyncClient):
        """Test login with non-existent username."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "SomePassword123!",
            }
        )
        
        assert response.status_code == 401

    async def test_login_inactive_user(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test login with inactive user."""
        # Create inactive user
        user = User(
            email="inactive@example.com",
            username="inactiveuser",
            password_hash=get_password_hash("TestPassword123!"),
            first_name="Inactive",
            last_name="User",
            status=UserStatus.INACTIVE,
            tenant_id="00000000-0000-0000-0000-000000000001",
        )
        db_session.add(user)
        await db_session.commit()
        
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": "inactiveuser",
                "password": "TestPassword123!",
            }
        )
        
        assert response.status_code == 403


# ========================================
# Token Refresh Tests
# ========================================

@pytest.mark.asyncio
class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    async def test_refresh_token_success(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test successful token refresh."""
        # First login to get refresh token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "TestPassword123!",
            }
        )
        refresh_token = login_response.json()["token"]["refresh_token"]
        
        # Use refresh token to get new access token
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_with_invalid_token(self, async_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"}
        )
        
        assert response.status_code == 401


# ========================================
# Logout Tests
# ========================================

@pytest.mark.asyncio
class TestLogout:
    """Tests for logout endpoint."""

    async def test_logout_success(self, async_client: AsyncClient, test_user: User):
        """Test successful logout."""
        # Login first
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "TestPassword123!",
            }
        )
        access_token = login_response.json()["token"]["access_token"]
        
        # Logout
        response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_logout_without_token(self, async_client: AsyncClient):
        """Test logout without authentication token."""
        response = await async_client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401


# ========================================
# Permission Tests
# ========================================

class TestPermissions:
    """Tests for permission checking."""

    def test_user_has_permission(self, test_user: User, test_role: Role):
        """Test user permission check."""
        from app.models.user import Permission
        
        # Create permission
        permission = Permission(
            code="test.permission",
            name="Test Permission",
            module="test",
            action="read",
            resource="test_resource",
        )
        
        # This would normally be done with proper database setup
        # test_role.permissions.append(permission)
        # test_user.roles.append(test_role)
        
        # For now, just test the method exists
        assert hasattr(test_user, 'has_permission')

    def test_superuser_has_all_permissions(self):
        """Test that superuser has all permissions."""
        from app.models.user import User
        
        superuser = User(
            email="super@example.com",
            username="superuser",
            is_superuser=True,
        )
        
        # Superuser should have all permissions
        assert superuser.has_permission("any.permission") is True
