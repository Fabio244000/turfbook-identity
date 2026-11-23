"""RSA keys for the session token tests: one pair per module, slow to generate."""

import base64
import json
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def key_pair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem.decode(), public_pem.decode()


@pytest.fixture(scope='module')
def keys() -> tuple[str, str]:
    return key_pair()


@pytest.fixture
def private_key(keys: tuple[str, str]) -> str:
    return keys[0]


@pytest.fixture
def public_key(keys: tuple[str, str]) -> str:
    return keys[1]


def tamper_subject(token: str) -> str:
    header, payload, signature = token.split('.')
    claims = json.loads(base64.urlsafe_b64decode(payload + '=='))
    claims['sub'] = str(uuid4())
    forged = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b'=')
    return f'{header}.{forged.decode()}.{signature}'
