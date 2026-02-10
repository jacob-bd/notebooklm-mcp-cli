
import pytest
import httpx
from unittest.mock import Mock, patch
from notebooklm_tools.core.retry import (
    is_retryable_error,
    execute_with_retry,
    retry_on_server_error,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BASE_DELAY
)

# Mock time.sleep to avoid waiting during tests
@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("time.sleep") as mock:
        yield mock

def test_is_retryable_error():
    # 5xx errors are retryable
    for status in [500, 502, 503, 504]:
        resp = httpx.Response(status)
        exc = httpx.HTTPStatusError("Error", request=Mock(), response=resp)
        assert is_retryable_error(exc) is True
    
    # 429 is retryable
    resp = httpx.Response(429)
    exc = httpx.HTTPStatusError("Error", request=Mock(), response=resp)
    assert is_retryable_error(exc) is True

    # 400, 401, 403, 404 are NOT retryable
    for status in [400, 401, 403, 404]:
        resp = httpx.Response(status)
        exc = httpx.HTTPStatusError("Error", request=Mock(), response=resp)
        assert is_retryable_error(exc) is False

    # Non-HTTP errors are not retryable (for this function)
    assert is_retryable_error(ValueError("foo")) is False

def test_execute_with_retry_success():
    func = Mock(return_value="success")
    result = execute_with_retry(func)
    assert result == "success"
    assert func.call_count == 1

def test_execute_with_retry_failure_then_success():
    # Fail twice with 503, then succeed
    resp_503 = httpx.Response(503)
    exc_503 = httpx.HTTPStatusError("Service Unavailable", request=Mock(), response=resp_503)
    
    func = Mock(side_effect=[exc_503, exc_503, "success"])
    
    result = execute_with_retry(func, max_retries=3)
    
    assert result == "success"
    assert func.call_count == 3

def test_execute_with_retry_max_retries_exceeded():
    # Always fail with 503
    resp_503 = httpx.Response(503)
    exc_503 = httpx.HTTPStatusError("Service Unavailable", request=Mock(), response=resp_503)
    
    func = Mock(side_effect=exc_503)
    
    with pytest.raises(httpx.HTTPStatusError):
        execute_with_retry(func, max_retries=2)
    
    # Called: initial + 2 retries = 3 total
    assert func.call_count == 3

def test_execute_with_retry_non_retryable_error():
    # Fail with 404 (not retryable)
    resp_404 = httpx.Response(404)
    exc_404 = httpx.HTTPStatusError("Not Found", request=Mock(), response=resp_404)
    
    func = Mock(side_effect=exc_404)
    
    with pytest.raises(httpx.HTTPStatusError):
        execute_with_retry(func)
    
    assert func.call_count == 1  # Should not retry

@retry_on_server_error(max_retries=2)
def decorated_function(mock_func):
    return mock_func()

def test_retry_decorator():
    # Fail once with 502, then succeed
    resp_502 = httpx.Response(502)
    exc_502 = httpx.HTTPStatusError("Bad Gateway", request=Mock(), response=resp_502)
    
    mock_func = Mock(side_effect=[exc_502, "decorated success"])
    
    result = decorated_function(mock_func)
    
    assert result == "decorated success"
    assert mock_func.call_count == 2
