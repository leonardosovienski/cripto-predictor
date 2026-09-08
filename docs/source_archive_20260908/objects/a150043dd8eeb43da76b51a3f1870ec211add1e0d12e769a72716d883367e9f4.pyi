from typing import Any

import httpx


def get_http_client(timeout: int = ...) -> httpx.AsyncClient: ...
def with_retry(*args: Any, **kwargs: Any) -> Any: ...


