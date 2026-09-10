import asyncio
import logging
import time
from typing import Callable, TypeVar
import openai

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRYABLE_EXCEPTIONS = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
    TimeoutError,
    ConnectionError,
)

NON_RETRYABLE_EXCEPTIONS = (
    openai.AuthenticationError,
    openai.BadRequestError,
    openai.PermissionDeniedError,
    openai.NotFoundError,
    ValueError,
    KeyError,
    TypeError,
)


def is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, NON_RETRYABLE_EXCEPTIONS):
        return False
    if isinstance(exc, RETRYABLE_EXCEPTIONS):
        return True
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code >= 500
    return False


def call_with_retry(
    func: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
) -> T:
    attempt = 0
    while True:
        try:
            return func()
        except Exception as exc:
            attempt += 1
            if attempt > max_retries or not is_retryable_exception(exc):
                logger.error(
                    "llm_call_failed",
                    extra={
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "retryable": is_retryable_exception(exc),
                        "error": str(exc),
                    },
                )
                raise exc
            delay = initial_delay * (backoff_factor ** (attempt - 1))
            logger.warning(
                "llm_call_retry",
                extra={
                    "attempt": attempt,
                    "max_retries": max_retries,
                    "delay_seconds": delay,
                    "error": str(exc),
                },
            )
            time.sleep(delay)


async def call_with_retry_async(
    func: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
) -> T:
    attempt = 0
    while True:
        try:
            return func()
        except Exception as exc:
            attempt += 1
            if attempt > max_retries or not is_retryable_exception(exc):
                logger.error(
                    "llm_call_failed",
                    extra={
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "retryable": is_retryable_exception(exc),
                        "error": str(exc),
                    },
                )
                raise exc
            delay = initial_delay * (backoff_factor ** (attempt - 1))
            logger.warning(
                "llm_call_retry",
                extra={
                    "attempt": attempt,
                    "max_retries": max_retries,
                    "delay_seconds": delay,
                    "error": str(exc),
                },
            )
            await asyncio.sleep(delay)
