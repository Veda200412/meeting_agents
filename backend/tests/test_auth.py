from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import pytest

from app.api.auth import get_current_user


def test_auth_uses_project_url_and_anon_key_to_validate_bearer_token():
    response = Mock(status_code=200)
    response.json.return_value = {"id": "user-123"}
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="user-access-token",
    )

    with patch(
        "app.api.auth.get_settings",
        return_value=SimpleNamespace(
            SUPABASE_URL="https://project.example/rest/v1/",
            SUPABASE_ANON_KEY="public-anon-key",
        ),
    ), patch("app.api.auth.httpx.get", return_value=response) as request:
        user = get_current_user(credentials)

    assert user == {"id": "user-123"}
    request.assert_called_once_with(
        "https://project.example/auth/v1/user",
        headers={
            "apikey": "public-anon-key",
            "Authorization": "Bearer user-access-token",
        },
        timeout=10,
    )


def test_auth_rejects_expired_user_token():
    response = Mock(status_code=401)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="expired-user-access-token",
    )

    with patch(
        "app.api.auth.get_settings",
        return_value=SimpleNamespace(
            SUPABASE_URL="https://project.example",
            SUPABASE_ANON_KEY="public-anon-key",
        ),
    ), patch("app.api.auth.httpx.get", return_value=response):
        with pytest.raises(HTTPException) as error:
            get_current_user(credentials)

    assert error.value.status_code == 401
    assert error.value.detail == "Supabase session is invalid or expired."
