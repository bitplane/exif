"""
Utility decorators
"""

import time
import logging
from functools import wraps

logger = logging.getLogger("editor")


def timed(func):
    """Decorator that logs execution time of a function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            logger.debug(f"{func.__name__} took {elapsed:.3f}s")
            return result
        except Exception:
            elapsed = time.time() - start
            logger.debug(f"{func.__name__} failed after {elapsed:.3f}s")
            raise
    return wrapper