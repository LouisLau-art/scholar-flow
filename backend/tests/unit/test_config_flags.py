from app.core import config as config_module


def test_allow_test_endpoints_enable_flag(monkeypatch):
    monkeypatch.setenv("ENABLE_TEST_ENDPOINTS", "true")
    monkeypatch.delenv("GO_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    assert config_module.allow_test_endpoints() is True


def test_allow_test_endpoints_env_names(monkeypatch):
    monkeypatch.delenv("ENABLE_TEST_ENDPOINTS", raising=False)
    monkeypatch.setenv("GO_ENV", "test")
    assert config_module.allow_test_endpoints() is True

    monkeypatch.setenv("GO_ENV", "development")
    assert config_module.allow_test_endpoints() is True

    monkeypatch.delenv("GO_ENV", raising=False)
    monkeypatch.setenv("ENV", "dev")
    assert config_module.allow_test_endpoints() is True


def test_crossref_mock_mode(monkeypatch):
    monkeypatch.setenv("CROSSREF_MOCK_MODE", "true")
    assert config_module.crossref_mock_mode() is True

    monkeypatch.setenv("CROSSREF_MOCK_MODE", "false")
    assert config_module.crossref_mock_mode() is False

