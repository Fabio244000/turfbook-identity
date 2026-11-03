from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.user_identity.infrastructure.api.schemas.api_response import (
    ApiErrorResponse,
    ApiResponse,
)
from app.user_identity.infrastructure.api.schemas.token_schema import (
    RefreshTokenRequest,
    SessionTokensData,
)
from app.user_identity.infrastructure.api.schemas.user_schema import (
    RegisterUserData,
    UserRequest,
)
from app.user_identity.main import app

# Public contract: FastAPI's documentation stays at the root.
OPENAPI_PATH = '/openapi.json'

# Every published operation, its request model, its success model and every response
# code of its contract (the ticket's §5).
OPERATIONS: dict[tuple[str, str], dict[str, Any]] = {
    ('/api/v1/users', 'post'): {
        'request': UserRequest,
        'success': ('201', ApiResponse[RegisterUserData]),
        'codes': {'201', '409', '422', '500'},
    },
    ('/api/v1/tokens', 'post'): {
        'request': RefreshTokenRequest,
        'success': ('200', ApiResponse[SessionTokensData]),
        'codes': {'200', '401', '422', '500'},
    },
    ('/api/v1/tokens/revoke', 'post'): {
        'request': RefreshTokenRequest,
        'success': ('204', None),
        'codes': {'204', '422', '500'},
    },
}


@pytest_asyncio.fixture
async def openapi() -> dict[str, Any]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get(OPENAPI_PATH)
    return dict(response.json())


def _operation(openapi: dict[str, Any], path: str, method: str) -> dict[str, Any]:
    return dict(openapi['paths'][path][method])


def _examples(content: dict[str, Any]) -> list[Any]:
    examples = content.get('application/json', {}).get('examples', {})
    return [example['value'] for example in examples.values()]


def _model_of(code: str, spec: dict[str, Any]) -> type[BaseModel] | None:
    success_code, success_model = spec['success']
    return success_model if code == success_code else ApiErrorResponse


class TestOpenApi:
    async def test_no_operation_is_published_without_its_documentation(self, openapi):
        published = {
            (path, method)
            for path, methods in openapi['paths'].items()
            for method in methods
        }

        assert published == set(OPERATIONS)

    @pytest.mark.parametrize('key', OPERATIONS, ids=lambda key: f'{key[1]} {key[0]}')
    async def test_documents_every_code_of_its_contract(self, openapi, key):
        responses = _operation(openapi, *key)['responses']

        assert set(responses) == OPERATIONS[key]['codes']

    @pytest.mark.parametrize('key', OPERATIONS, ids=lambda key: f'{key[1]} {key[0]}')
    async def test_errors_use_the_error_envelope(self, openapi, key):
        responses = _operation(openapi, *key)['responses']

        for code, response in responses.items():
            if code.startswith(('4', '5')):
                schema = response['content']['application/json']['schema']
                assert schema['$ref'].endswith('/ApiErrorResponse'), code

    @pytest.mark.parametrize('key', OPERATIONS, ids=lambda key: f'{key[1]} {key[0]}')
    async def test_has_a_summary_and_a_description(self, openapi, key):
        operation = _operation(openapi, *key)

        assert operation.get('summary')
        assert operation.get('description')

    @pytest.mark.parametrize('key', OPERATIONS, ids=lambda key: f'{key[1]} {key[0]}')
    async def test_request_examples_are_valid_requests(self, openapi, key):
        content = _operation(openapi, *key)['requestBody']['content']

        examples = _examples(content)

        assert examples
        for example in examples:
            OPERATIONS[key]['request'].model_validate(example)

    @pytest.mark.parametrize('key', OPERATIONS, ids=lambda key: f'{key[1]} {key[0]}')
    async def test_response_examples_match_their_model(self, openapi, key):
        responses = _operation(openapi, *key)['responses']

        for code, response in responses.items():
            model = _model_of(code, OPERATIONS[key])
            examples = _examples(response.get('content', {}))
            assert examples or model is None, code
            for example in examples:
                assert model is not None
                model.model_validate(example)
