import pytest

from app.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher


@pytest.fixture
def hasher():
    return Argon2PasswordHasher()


def test_hash_is_not_the_plain_password(hasher):
    password = 'secret1234'
    hashed = hasher.hash(password)
    assert hashed != password


def test_hash_is_not_empty(hasher):
    hashed = hasher.hash('secret1234')
    assert hashed


def test_same_password_produces_different_hashes(hasher):
    password = 'secret1234'
    first = hasher.hash(password)
    second = hasher.hash(password)
    assert first != second


def test_hash_has_argon2_format(hasher):
    hashed = hasher.hash('secret1234')
    assert hashed.startswith('$argon2')


def test_verify_returns_true_for_correct_password(hasher):
    password = 'secret1234'
    hashed = hasher.hash(password)
    assert hasher.verify(password, hashed) is True


def test_verify_returns_false_for_wrong_password(hasher):
    hashed = hasher.hash('secret1234')
    assert hasher.verify('wrongpassword', hashed) is False
