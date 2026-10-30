from fastapi import FastAPI
from mangum import Mangum

from app.user_identity.domain.exceptions import DomainError
from app.user_identity.infrastructure.api.exception_handlers import (
    domain_exception_handler,
)
from app.user_identity.infrastructure.api.v1_router import router as v1_router
from config.settings import settings

app = FastAPI(title='TurfBoor User Service')

app.include_router(v1_router, prefix=settings.api_prefix)
app.add_exception_handler(DomainError, domain_exception_handler)

handler = Mangum(app, lifespan='off')
