from pathlib import Path

from merit_assistant.profiles.loader import load_profile


def test_initial_profile_contains_only_expected_metadata() -> None:
    profile = load_profile(
        Path("config/profiles/finep_mais_inovacao_tecnologias_digitais/profile.yaml")
    )
    assert profile.id == "finep_mais_inovacao_tecnologias_digitais"
    assert profile.status == "active"
