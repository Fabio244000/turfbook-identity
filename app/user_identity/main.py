from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from mangum import Mangum

from app.user_identity.domain.exceptions import DomainError
from app.user_identity.infrastructure.api.exception_handlers import (
    domain_exception_handler,
    request_validation_handler,
    unexpected_exception_handler,
)
from app.user_identity.infrastructure.api.v1_router import router as v1_router
from config.settings import settings

app = FastAPI(title='TurfBoor User Service')

app.include_router(v1_router, prefix=settings.api_prefix)
app.add_exception_handler(DomainError, domain_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)

KEEP_WARM_KEY = 'keep_warm'  # the keep-warm schedule's input
_http_handler = Mangum(app, lifespan='off')


def handler(event: dict[str, Any], context: Any) -> Any:
    """Lambda entry point; the keep-warm schedule only wakes the environment."""
    if event.get(KEEP_WARM_KEY):
        return None
    return _http_handler(event, context)
