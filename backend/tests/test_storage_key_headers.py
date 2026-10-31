import pytest

from app.services.storage import storage_headers


@pytest.mark.parametrize('upload', [False, True])
@pytest.mark.parametrize('key', ['sb_secret_synthetic_unit_test_only', 'legacy-jwt-test-placeholder'])
def test_private_storage_headers_distinguish_secret_keys_from_jwts(key, upload):
    headers = storage_headers(key, upload=upload)
    assert headers['apikey'] == key
    if key.startswith('sb_secret_'):
        assert 'Authorization' not in headers
    else:
        assert headers['Authorization'] == f'Bearer {key}'
    assert ('Content-Type' in headers) == upload
