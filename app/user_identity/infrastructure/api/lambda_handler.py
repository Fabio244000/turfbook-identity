from collections.abc import Callable
from typing import Any

from fastapi import FastAPI
from mangum import Mangum

KEEP_WARM_KEY = 'keep_warm'  # the keep-warm schedule's input


def lambda_handler(app: FastAPI) -> Callable[[dict[str, Any], Any], Any]:
    """The Lambda entry point of an API; the keep-warm schedule only wakes the
    environment, and never reaches the app."""
    http_handler = Mangum(app, lifespan='off')

    def handler(event: dict[str, Any], context: Any) -> Any:
        if event.get(KEEP_WARM_KEY):
            return None
        return http_handler(event, context)

    return handler
