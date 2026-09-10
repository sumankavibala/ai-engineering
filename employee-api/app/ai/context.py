import contextvars

_request_id_ctx_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


def set_request_id(request_id: str) -> None:
    _request_id_ctx_var.set(request_id)


def get_request_id() -> str | None:
    return _request_id_ctx_var.get()
