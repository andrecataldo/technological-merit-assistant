from merit_assistant.config.settings import Settings


def test_external_processing_is_disabled_by_default() -> None:
    settings = Settings(_env_file=None)
    assert settings.external_processing_enabled is False
