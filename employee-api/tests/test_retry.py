import pytest
import openai
from unittest.mock import MagicMock
from app.ai.retry import call_with_retry, is_retryable_exception


def test_is_retryable_exception():
    assert is_retryable_exception(openai.APIConnectionError(request=MagicMock())) is True
    assert is_retryable_exception(openai.APITimeoutError(request=MagicMock())) is True
    assert is_retryable_exception(openai.RateLimitError(message="rate limit", response=MagicMock(status_code=429), body=None)) is True

    assert is_retryable_exception(openai.AuthenticationError(message="auth fail", response=MagicMock(status_code=401), body=None)) is False
    assert is_retryable_exception(openai.BadRequestError(message="bad req", response=MagicMock(status_code=400), body=None)) is False


def test_call_with_retry_success():
    mock_func = MagicMock(return_value="success")
    res = call_with_retry(mock_func, max_retries=2, initial_delay=0.01)
    assert res == "success"
    assert mock_func.call_count == 1


def test_call_with_retry_retries_on_retryable_error():
    mock_func = MagicMock(side_effect=[
        openai.APIConnectionError(request=MagicMock()),
        "success after retry"
    ])
    res = call_with_retry(mock_func, max_retries=2, initial_delay=0.01)
    assert res == "success after retry"
    assert mock_func.call_count == 2


def test_call_with_retry_raises_non_retryable_error_immediately():
    mock_func = MagicMock(side_effect=openai.BadRequestError(message="bad req", response=MagicMock(status_code=400), body=None))
    with pytest.raises(openai.BadRequestError):
        call_with_retry(mock_func, max_retries=3, initial_delay=0.01)
    assert mock_func.call_count == 1
