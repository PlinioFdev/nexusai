from fastapi.testclient import TestClient


def _register(client: TestClient, slug: str = "acme", email: str = "owner@acme.com") -> dict:
    payload = {
        "tenant_data": {"name": slug.capitalize(), "slug": slug},
        "user_data": {"email": email, "password": "secret123", "full_name": "Test User"},
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, res.json()
    return res.json()


def _login(client: TestClient, slug: str = "acme", email: str = "owner@acme.com") -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "secret123", "slug": slug},
    )
    assert res.status_code == 200, res.json()
    return res.json()["access_token"]


class TestRegister:
    def test_register_creates_tenant_and_owner(self, client: TestClient):
        user = _register(client)
        assert user["email"] == "owner@acme.com"
        assert user["role"] == "OWNER"
        assert "tenant_id" in user

    def test_register_duplicate_slug_fails(self, client: TestClient):
        _register(client, slug="acme")
        res = client.post(
            "/api/v1/auth/register",
            json={
                "tenant_data": {"name": "Other", "slug": "acme"},
                "user_data": {"email": "other@acme.com", "password": "secret123", "full_name": "Other"},
            },
        )
        assert res.status_code == 422

    def test_register_weak_password_fails(self, client: TestClient):
        res = client.post(
            "/api/v1/auth/register",
            json={
                "tenant_data": {"name": "Weak", "slug": "weak"},
                "user_data": {"email": "u@weak.com", "password": "123", "full_name": "U"},
            },
        )
        assert res.status_code == 422

    def test_register_invalid_slug_fails(self, client: TestClient):
        res = client.post(
            "/api/v1/auth/register",
            json={
                "tenant_data": {"name": "Bad Slug", "slug": "Bad Slug!"},
                "user_data": {"email": "u@bad.com", "password": "secret123", "full_name": "U"},
            },
        )
        assert res.status_code == 422


class TestLogin:
    def test_login_returns_access_token(self, client: TestClient):
        _register(client)
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@acme.com", "password": "secret123", "slug": "acme"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_fails(self, client: TestClient):
        _register(client)
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@acme.com", "password": "wrongpass", "slug": "acme"},
        )
        assert res.status_code == 401

    def test_login_unknown_email_fails(self, client: TestClient):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@acme.com", "password": "secret123", "slug": "acme"},
        )
        assert res.status_code == 401

    def test_login_wrong_slug_fails(self, client: TestClient):
        """Usuário existe mas slug errado — deve falhar com 401."""
        _register(client, slug="acme")
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@acme.com", "password": "secret123", "slug": "wrong-slug"},
        )
        assert res.status_code == 401

    def test_login_invalid_slug_format_fails(self, client: TestClient):
        """Slug com formato inválido deve falhar com 422."""
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@acme.com", "password": "secret123", "slug": "INVALID SLUG!"},
        )
        assert res.status_code == 422

    def test_same_email_different_tenants_login_correctly(self, client: TestClient):
        """Email igual em tenants diferentes — cada um só autentica no seu tenant."""
        _register(client, slug="tenant-a", email="shared@email.com")
        _register(client, slug="tenant-b", email="shared@email.com")

        res_a = client.post(
            "/api/v1/auth/login",
            json={"email": "shared@email.com", "password": "secret123", "slug": "tenant-a"},
        )
        res_b = client.post(
            "/api/v1/auth/login",
            json={"email": "shared@email.com", "password": "secret123", "slug": "tenant-b"},
        )
        assert res_a.status_code == 200
        assert res_b.status_code == 200
        # Tokens diferentes — tenants diferentes
        assert res_a.json()["access_token"] != res_b.json()["access_token"]


class TestMultiTenancy:
    def test_same_email_allowed_in_different_tenants(self, client: TestClient):
        _register(client, slug="tenant-a", email="shared@email.com")
        user_b = _register(client, slug="tenant-b", email="shared@email.com")
        assert user_b["email"] == "shared@email.com"


class TestHealth:
    def test_health_check(self, client: TestClient):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
