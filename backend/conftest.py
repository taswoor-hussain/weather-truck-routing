import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def isolated_cache():
    """Each test starts with an empty cache (weather, heatmaps and throttle counters)."""
    cache.clear()
    yield
    cache.clear()
