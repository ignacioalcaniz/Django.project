import pytest


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    """All pytest suites are offline, including regressions outside pagos."""
    def forbidden(*args, **kwargs):
        raise AssertionError("Real HTTP is forbidden in tests; mock the provider client.")
    monkeypatch.setattr("requests.sessions.Session.request", forbidden)
