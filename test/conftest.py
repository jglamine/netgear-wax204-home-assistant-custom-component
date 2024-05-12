import os
import pytest
import pytest_socket
import pytest_homeassistant_custom_component.plugins as ha_plugin


@pytest.hookimpl(tryfirst=True)
def pytest_configure() -> None:
    """Disable pytest_socket and freezegun from home assistant plugin.

    The default home assistant fixtures disable access to non-localhost sockets.
    They also mock all datetimes, breaking datetime.now().

    Monkey patch to skip pytest_socket and freezegun setup.
    """
    def noop(): return None
    def disable_socket_noop(allow_unix_socket=False): return None

    def disable_socket_allow_hosts(
        allowed=None, allow_unix_socket=False): return None

    # Monkey patch to disable freezegun datetime mocking in home assistant fixtures.
    ha_plugin.pytest_runtest_setup = noop

    # Monkey patch to disable pytest_socket
    pytest_socket.pytest_runtest_setup = noop
    pytest_socket.disable_socket = disable_socket_noop
    pytest_socket.socket_allow_hosts = disable_socket_allow_hosts


@pytest.fixture(scope="module")
def test_data() -> str:
    dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(dir, "test-data.properties")

    d = {}
    with open(file_path) as f:
        for line in f:
            if line.startswith("#") or line.strip() == "":
                continue
            key, value = line.strip().split("=")
            d[key] = value

    return d


def read_property(test_data, key) -> str:
    try:
        return test_data[key]
    except KeyError:
        raise KeyError(f"Missing {key} in test-data.properties")


@pytest.fixture
def router_host(test_data) -> str:
    return read_property(test_data, "router_host")


@pytest.fixture
def router_password(test_data) -> str:
    return read_property(test_data, "router_password")
