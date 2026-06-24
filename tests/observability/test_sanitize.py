from app.observability.logging_config import sanitize_headers


def test_sanitize_redacts_rapidapi_key():
    result = sanitize_headers({"x-rapidapi-key": "secret123", "content-type": "application/json"})
    assert result["x-rapidapi-key"] == "[REDACTED]"
    assert result["content-type"] == "application/json"


def test_sanitize_redacts_auth_token_case_insensitive():
    result = sanitize_headers({"X-Auth-Token": "secret456"})
    assert result["X-Auth-Token"] == "[REDACTED]"


def test_sanitize_redacts_authorization():
    result = sanitize_headers({"Authorization": "Bearer token123"})
    assert result["Authorization"] == "[REDACTED]"


def test_sanitize_preserves_non_auth_headers():
    headers = {"content-type": "application/json", "accept": "application/json"}
    result = sanitize_headers(headers)
    assert result == headers


def test_sanitize_key_not_in_sanitized_string():
    fake_key = "SUPER_SECRET_KEY_DO_NOT_LOG"
    result = sanitize_headers({"x-rapidapi-key": fake_key})
    assert fake_key not in str(result)
