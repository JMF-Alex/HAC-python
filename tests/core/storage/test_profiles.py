import pytest

from core.storage import profiles


def test_name_error_accepts_a_valid_name():
    assert profiles.name_error("Gaming", ["Default"]) is None


def test_name_error_rejects_empty_names():
    assert profiles.name_error("   ", []) == "Enter a name"


def test_name_error_rejects_long_names():
    assert profiles.name_error("x" * (profiles.MAX_PROFILE_NAME + 1), []) is not None
    assert profiles.name_error("x" * profiles.MAX_PROFILE_NAME, []) is None


def test_name_error_ignores_surrounding_spaces():
    assert profiles.name_error("  Gaming  ", ["Default"]) is None
    assert profiles.name_error("  default ", ["Default"]) is not None


def test_name_error_rejects_duplicates_ignoring_case():
    assert profiles.name_error("default", ["Default"]) is not None


def test_name_error_allows_keeping_the_name_being_renamed():
    assert profiles.name_error("Default", ["Default", "Other"], ignore="Default") is None
    assert profiles.name_error("Other", ["Default", "Other"], ignore="Default") is not None


def test_unique_name_adds_a_numeric_suffix():
    assert profiles.unique_name("Profile", []) == "Profile"
    assert profiles.unique_name("Profile", ["Profile"]) == "Profile 2"
    assert profiles.unique_name("Profile", ["profile", "Profile 2"]) == "Profile 3"


def test_suggest_hotkey_skips_taken_keys():
    assert profiles.suggest_hotkey([]) == "F6"
    assert profiles.suggest_hotkey(["F6", "f7", ""]) == "F8"


def test_suggest_hotkey_returns_empty_when_everything_is_taken():
    assert profiles.suggest_hotkey([f"F{n}" for n in range(6, 13)]) == ""


def test_copy_name_appends_copy():
    assert profiles.copy_name("Gaming", ["Gaming"]) == "Gaming copy"


def test_copy_name_numbers_further_copies():
    taken = ["Gaming", "Gaming copy"]
    assert profiles.copy_name("Gaming", taken) == "Gaming copy 2"
    assert profiles.copy_name("Gaming", taken + ["Gaming copy 2"]) == "Gaming copy 3"


def test_copy_name_is_case_insensitive_about_clashes():
    assert profiles.copy_name("Gaming", ["Gaming", "GAMING COPY"]) == "Gaming copy 2"


def test_copy_name_of_a_copy_keeps_growing_a_suffix():
    assert profiles.copy_name("Gaming copy", ["Gaming copy"]) == "Gaming copy copy"


@pytest.mark.parametrize("name", ["x" * profiles.MAX_PROFILE_NAME, "W" * profiles.MAX_PROFILE_NAME])
def test_copy_name_never_exceeds_the_name_limit(name):
    taken = [name]
    for _ in range(12):
        copy = profiles.copy_name(name, taken)
        assert profiles.name_error(copy, taken) is None
        assert len(copy) <= profiles.MAX_PROFILE_NAME
        taken.append(copy)
    assert len(set(taken)) == 13
