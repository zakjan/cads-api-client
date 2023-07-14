import os
from typing import Any

import pytest


@pytest.fixture
def api_root_url() -> str:
    from cads_api_client import config

    return config.get_config("url")


@pytest.fixture
def api_key() -> str:
    # default to anonymous access for tests
    return os.getenv("CADS_API_KEY") or "00112233-4455-6677-c899-aabbccddeeff"


@pytest.fixture
def request_year() -> str:
    return os.environ.get("CADS_TEST_YEAR", "2016")


@pytest.fixture()
def temp_environ() -> Any:
    """Create a modifiable environment that affect only the test scope."""
    old_environ = dict(os.environ)

    yield os.environ

    os.environ.clear()
    os.environ.update(old_environ)
