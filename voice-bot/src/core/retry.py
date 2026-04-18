"""Retry decorator with exponential backoff for service calls."""
import time
import functools
from typing import Callable, Type, Tuple

def retry(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    logger=None
):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        sleep_time = delay * (backoff ** attempt)
                        if logger:
                            logger.warning(
                                f"Retry {attempt+1}/{max_retries} after {sleep_time:.1f}s: {e}"
                            )
                        time.sleep(sleep_time)
                    else:
                        if logger:
                            logger.error(f"All retries exhausted: {e}")
            raise last_exception
        return wrapper
    return decorator