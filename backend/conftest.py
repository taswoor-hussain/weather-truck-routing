import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def test_settings(settings):
    """Tests must not depend on the local .env: the test client speaks plain HTTP."""
    settings.SECURE_SSL_REDIRECT = False


@pytest.fixture(autouse=True)
def isolated_cache():
    """Each test starts with an empty cache (weather, heatmaps and throttle counters)."""
    cache.clear()
    yield
    cache.clear()
