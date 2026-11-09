from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.user_identity.accounts_main import app as accounts_app
from app.user_identity.infrastructure.api.schemas.account_schema import (
    AccountStatusData,
    AccountStatusRequest,
)
from app.user_identity.infrastructure.api.schemas.api_response import (
    ApiErrorResponse,
    ApiResponse,
)
from app.user_identity.infrastructure.api.schemas.session_schema import (
    SessionRequest,
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

# Public contract: FastAPI's documentation stays at the root of each API.
OPENAPI_PATH = '/openapi.json'

# Each API (its own Lambda and API Gateway) and its title.
APPS: dict[str, tuple[FastAPI, str]] = {
    'identity': (app, 'TurfBook User Service'),
    'accounts': (accounts_app, 'TurfBook Accounts Service'),
}

# Every published operation (API, path, method), its request model, its success model,
# every response code of its contract (the ticket's §5) and its security, if any.
OPERATIONS: dict[tuple[str, str, str], dict[str, Any]] = {
    ('identity', '/api/v1/users', 'post'): {
        'request': UserRequest,
        'success': ('201', ApiResponse[RegisterUserData]),
        'codes': {'201', '409', '422', '500'},
    },
    ('identity', '/api/v1/sessions', 'post'): {
        'request': SessionRequest,
        'success': ('201', ApiResponse[SessionTokensData]),
        'codes': {'201', '401', '403', '422', '500'},
    },
    ('identity', '/api/v1/tokens', 'post'): {
        'request': RefreshTokenRequest,
        'success': ('200', ApiResponse[SessionTokensData]),
        'codes': {'200', '401', '422', '500'},
    },
    ('identity', '/api/v1/tokens/revoke', 'post'): {
        'request': RefreshTokenRequest,
        'success': ('204', None),
        'codes': {'204', '422', '500'},
    },
    ('accounts', '/api/v1/accounts/{user_uuid}', 'patch'): {
        'request': AccountStatusRequest,
        'success': ('200', ApiResponse[AccountStatusData]),
        'codes': {'200', '401', '404', '409', '422', '500'},
        'api_key_header': 'X-Api-Key',
    },
}
SECURED = [key for key, spec in OPERATIONS.items() if 'api_key_header' in spec]


def _id(key: tuple[str, str, str]) -> str:
    return f'{key[0]}: {key[2]} {key[1]}'


@pytest_asyncio.fixture
async def openapis() -> dict[str, dict[str, Any]]:
    specs = {}
    for name, (api, _) in APPS.items():
        transport = ASGITransport(app=api)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            specs[name] = dict((await client.get(OPENAPI_PATH)).json())
    return specs


def _operation(
    openapis: dict[str, dict[str, Any]], key: tuple[str, str, str]
) -> dict[str, Any]:
    api, path, method = key
    return dict(openapis[api]['paths'][path][method])


def _examples(content: dict[str, Any]) -> list[Any]:
    examples = content.get('application/json', {}).get('examples', {})
    return [example['value'] for example in examples.values()]


def _model_of(code: str, spec: dict[str, Any]) -> type[BaseModel] | None:
    success_code, success_model = spec['success']
    return success_model if code == success_code else ApiErrorResponse


class TestOpenApi:
    @pytest.mark.parametrize('api', APPS)
    async def test_is_titled_with_the_service_name(self, openapis, api):
        assert openapis[api]['info']['title'] == APPS[api][1]

    @pytest.mark.parametrize('api', APPS)
    async def test_no_operation_is_published_without_its_documentation(
        self, openapis, api
    ):
        published = {
            (api, path, method)
            for path, methods in openapis[api]['paths'].items()
            for method in methods
        }

        assert published == {key for key in OPERATIONS if key[0] == api}

    @pytest.mark.parametrize('key', OPERATIONS, ids=_id)
    async def test_documents_every_code_of_its_contract(self, openapis, key):
        responses = _operation(openapis, key)['responses']

        assert set(responses) == OPERATIONS[key]['codes']

    @pytest.mark.parametrize('key', OPERATIONS, ids=_id)
    async def test_errors_use_the_error_envelope(self, openapis, key):
        responses = _operation(openapis, key)['responses']

        for code, response in responses.items():
            if code.startswith(('4', '5')):
                schema = response['content']['application/json']['schema']
                assert schema['$ref'].endswith('/ApiErrorResponse'), code

    @pytest.mark.parametrize('key', OPERATIONS, ids=_id)
    async def test_has_a_summary_and_a_description(self, openapis, key):
        operation = _operation(openapis, key)

        assert operation.get('summary')
        assert operation.get('description')

    @pytest.mark.parametrize('key', OPERATIONS, ids=_id)
    async def test_request_examples_are_valid_requests(self, openapis, key):
        content = _operation(openapis, key)['requestBody']['content']

        examples = _examples(content)

        assert examples
        for example in examples:
            OPERATIONS[key]['request'].model_validate(example)

    @pytest.mark.parametrize('key', OPERATIONS, ids=_id)
    async def test_response_examples_match_their_model(self, openapis, key):
        responses = _operation(openapis, key)['responses']

        for code, response in responses.items():
            model = _model_of(code, OPERATIONS[key])
            examples = _examples(response.get('content', {}))
            assert examples or model is None, code
            for example in examples:
                assert model is not None
                model.model_validate(example)

    @pytest.mark.parametrize('key', SECURED, ids=_id)
    async def test_declares_the_api_key_it_needs(self, openapis, key):
        [requirement] = _operation(openapis, key)['security']
        [scheme_name] = requirement
        scheme = openapis[key[0]]['components']['securitySchemes'][scheme_name]

        assert (scheme['type'], scheme['in'], scheme['name']) == (
            'apiKey',
            'header',
            OPERATIONS[key]['api_key_header'],
        )
