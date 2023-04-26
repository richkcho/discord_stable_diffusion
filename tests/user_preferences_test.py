
import os

from modules.user_preferences import UserPreferences, save_preferences, load_preferences


def test_user_preferences_empty():
    user_prefs = UserPreferences()

    assert user_prefs.get_preference(1, "some_pref") is None
    assert not user_prefs.to_dict()


def test_user_preferences_simple_set():
    user_prefs = UserPreferences()

    user = 1
    test_values = {
        "foo_str": "foooo",
        "bar_int": 1,
        "baz_bool": True,
        "meow_float": 1.69
    }

    for name, value in test_values.items():
        user_prefs.set_preference(user, name, value)

    for name, value in test_values.items():
        saved_value = user_prefs.get_preference(user, name)
        assert value == saved_value


def test_user_preferences_load_save():
    user_prefs = UserPreferences()

    user = 1
    test_values = {
        "foo_str": "foooo",
        "bar_int": 1,
        "baz_bool": True,
        "meow_float": 1.69
    }

    for name, value in test_values.items():
        user_prefs.set_preference(user, name, value)

    test_path = "test.json"
    save_preferences(user_prefs, test_path)

    user_prefs = load_preferences(test_path)

    for name, value in test_values.items():
        saved_value = user_prefs.get_preference(user, name)
        assert value == saved_value

    os.unlink(test_path)
