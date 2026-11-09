"""Lambda `accounts`: TurfBook's API to manage accounts, with its own API Gateway."""

from fastapi import FastAPI

from app.user_identity.infrastructure.api.accounts_v1_router import (
    router as accounts_v1_router,
)
from app.user_identity.infrastructure.api.exception_handlers import (
    register_exception_handlers,
)
from app.user_identity.infrastructure.api.lambda_handler import lambda_handler
from config.settings import settings

app = FastAPI(title='TurfBook Accounts Service')

app.include_router(accounts_v1_router, prefix=settings.api_prefix)
register_exception_handlers(app)

handler = lambda_handler(app)
