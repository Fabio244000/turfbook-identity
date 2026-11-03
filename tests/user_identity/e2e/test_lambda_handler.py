import asyncio
from collections.abc import Iterator
from typing import Any

import pytest

from app.user_identity.main import handler

# The keep-warm schedule's input (`deploy/resources/keep-warm.yml`).
KEEP_WARM_EVENT = {'keep_warm': True}


def _http_event(path: str) -> dict[str, Any]:
    """A minimal API Gateway HTTP API event (payload 2.0)."""
    return {
        'version': '2.0',
        'routeKey': '$default',
        'rawPath': path,
        'rawQueryString': '',
        'headers': {'host': 'qwgogln6g2.execute-api.us-east-1.amazonaws.com'},
        'requestContext': {
            'http': {
                'method': 'GET',
                'path': path,
                'protocol': 'HTTP/1.1',
                'sourceIp': '190.42.10.7',
                'userAgent': 'test',
            },
            'stage': '$default',
        },
        'isBase64Encoded': False,
    }


@pytest.fixture
def lambda_event_loop() -> Iterator[None]:
    """Mangum takes the thread's event loop, as in Lambda; pytest-asyncio leaves the main
    thread without one after the async tests, so this test gets its own."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()
    asyncio.set_event_loop(None)


class TestLambdaHandler:
    def test_the_keep_warm_schedule_is_answered_without_reaching_the_app(self):
        response = handler(KEEP_WARM_EVENT, None)

        assert response is None

    def test_an_http_event_still_reaches_the_api(self, lambda_event_loop):
        response = handler(_http_event('/openapi.json'), None)

        assert response['statusCode'] == 200
