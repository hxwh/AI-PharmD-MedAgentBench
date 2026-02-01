"""Test configuration for Purple Agent."""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--agent-url",
        action="store",
        default="http://localhost:9019",
        help="URL of the running agent"
    )


@pytest.fixture
def agent_url(request):
    return request.config.getoption("--agent-url")
