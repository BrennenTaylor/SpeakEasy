from pathlib import Path

import pytest


def test_ai_settings_defaults_and_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.core.config import Settings

    monkeypatch.chdir(tmp_path)
    settings = Settings()
    assert settings.openai_api_key is None
    assert settings.ai_model == "gpt-6-luna"
    assert settings.ai_timeout_seconds == 10.0
    assert settings.usda_api_key == "DEMO_KEY"

    monkeypatch.setenv("APP_OPENAI_API_KEY", "server-only-key")
    monkeypatch.setenv("APP_AI_MODEL", "gpt-6.1-terra")
    assert Settings().openai_api_key == "server-only-key"
    assert Settings().ai_model == "gpt-6.1-terra"
