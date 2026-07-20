from typing import Any

from market_connector.app import serve


def test_serve_uses_settings_from_environment(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_run(app: str, **kwargs: Any) -> None:
        captured['app'] = app
        captured.update(kwargs)

    monkeypatch.setenv('MARKET_CONNECTOR_API_HOST', '0.0.0.0')
    monkeypatch.setenv('MARKET_CONNECTOR_API_PORT', '9000')
    monkeypatch.setenv('MARKET_CONNECTOR_API_RELOAD', 'true')
    monkeypatch.setattr(serve.uvicorn, 'run', fake_run)

    serve.main()

    assert captured == {
        'app': 'market_connector.app.main:app',
        'host': '0.0.0.0',
        'port': 9000,
        'reload': True,
    }
