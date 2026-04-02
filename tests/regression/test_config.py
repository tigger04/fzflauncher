# ABOUTME: Regression tests for configuration loading and validation (issue #2).
# ABOUTME: Covers defaults, user overrides, tilde expansion, immutability, and error handling.

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from fzflauncher.config import Config, ConfigError, load_config


@pytest.fixture
def default_config_path(project_root):
    return project_root / "config" / "default.yaml"


@pytest.fixture
def user_config_absent(tmp_path):
    """A path that does not exist."""
    return tmp_path / "nonexistent.yaml"


@pytest.fixture
def user_config(tmp_path):
    """Helper: write a user config dict to a temp file and return its path."""

    def _write(data: dict) -> Path:
        path = tmp_path / "config.yaml"
        path.write_text(yaml.dump(data))
        return path

    return _write


# ---------------------------------------------------------------------------
# AC2.1 — Default configuration loaded when no user config exists
# ---------------------------------------------------------------------------


def test_load_config_defaults_present_when_no_user_config_RT2_1(
    default_config_path, user_config_absent
):
    """RT-2.1: Load with non-existent user config path; all default values present."""
    config = load_config(
        user_config_path=user_config_absent,
        default_config_path=default_config_path,
    )
    assert config.paths.applications
    assert isinstance(config.paths.use_bundle_name, bool)
    assert config.display.opacity == pytest.approx(0.90)
    assert config.display.width == 80
    assert config.display.height == 20
    assert config.display.position == "center"
    assert config.fzf.options
    assert config.hotkey.global_hotkey


def test_load_config_defaults_all_required_keys_RT2_2(
    default_config_path, user_config_absent
):
    """RT-2.2: Default config contains all required keys."""
    config = load_config(
        user_config_path=user_config_absent,
        default_config_path=default_config_path,
    )
    assert isinstance(config, Config)
    assert config.paths is not None
    assert config.display is not None
    assert config.fzf is not None
    assert config.hotkey is not None
    assert len(config.paths.applications) > 0
    assert config.fzf.options != ""
    assert config.hotkey.global_hotkey != ""


# ---------------------------------------------------------------------------
# AC2.2 — User configuration values override defaults
# ---------------------------------------------------------------------------


def test_user_config_scalar_overrides_default_RT2_3(default_config_path, user_config):
    """RT-2.3: User config with different opacity overrides the default."""
    path = user_config({"display": {"opacity": 0.5}})
    config = load_config(user_config_path=path, default_config_path=default_config_path)
    assert config.display.opacity == pytest.approx(0.5)


def test_user_config_list_replaces_default_RT2_4(default_config_path, user_config):
    """RT-2.4: User config with different applications list replaces the default list."""
    path = user_config({"paths": {"applications": ["/opt/apps"]}})
    config = load_config(user_config_path=path, default_config_path=default_config_path)
    assert config.paths.applications == ("/opt/apps",)


def test_partial_user_config_preserves_other_defaults_RT2_5(
    default_config_path, user_config
):
    """RT-2.5: Partial user config (one section only) preserves other sections' defaults."""
    path = user_config({"display": {"opacity": 0.7}})
    config = load_config(user_config_path=path, default_config_path=default_config_path)
    # Modified section
    assert config.display.opacity == pytest.approx(0.7)
    # Untouched sections retain defaults
    assert config.display.width == 80
    assert len(config.paths.applications) > 0
    assert config.fzf.options != ""


# ---------------------------------------------------------------------------
# AC2.3 — Tilde expansion in path values
# ---------------------------------------------------------------------------


def test_tilde_in_path_is_expanded_RT2_6(default_config_path, user_config_absent):
    """RT-2.6: Paths containing ~ are expanded to absolute paths."""
    config = load_config(
        user_config_path=user_config_absent,
        default_config_path=default_config_path,
    )
    for app_path in config.paths.applications:
        assert not app_path.startswith("~"), f"Path not expanded: {app_path}"
        assert app_path.startswith("/")


def test_absolute_path_unchanged_RT2_7(default_config_path, user_config_absent):
    """RT-2.7: Absolute paths like /Applications are unchanged."""
    config = load_config(
        user_config_path=user_config_absent,
        default_config_path=default_config_path,
    )
    assert "/Applications" in config.paths.applications


# ---------------------------------------------------------------------------
# AC2.4 — Configuration object is immutable after loading
# ---------------------------------------------------------------------------


def test_top_level_attribute_immutable_RT2_8(default_config_path, user_config_absent):
    """RT-2.8: Modifying a top-level config attribute raises FrozenInstanceError."""
    config = load_config(
        user_config_path=user_config_absent,
        default_config_path=default_config_path,
    )
    with pytest.raises(FrozenInstanceError):
        config.fzf = None  # type: ignore[misc]


def test_nested_attribute_immutable_RT2_9(default_config_path, user_config_absent):
    """RT-2.9: Modifying a nested config attribute raises FrozenInstanceError."""
    config = load_config(
        user_config_path=user_config_absent,
        default_config_path=default_config_path,
    )
    with pytest.raises(FrozenInstanceError):
        config.display.width = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AC2.5 — Invalid configuration raises specific, actionable errors
# ---------------------------------------------------------------------------


def test_invalid_yaml_syntax_raises_config_error_RT2_10(default_config_path, tmp_path):
    """RT-2.10: Invalid YAML syntax raises a descriptive ConfigError."""
    bad = tmp_path / "bad.yaml"
    bad.write_text("display: {\n  unclosed bracket")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(user_config_path=bad, default_config_path=default_config_path)


def test_wrong_type_raises_config_error_naming_field_RT2_11(
    default_config_path, user_config
):
    """RT-2.11: Wrong type (string where int expected) raises error naming the field."""
    path = user_config({"display": {"width": "wide"}})
    with pytest.raises(ConfigError, match="display.width"):
        load_config(user_config_path=path, default_config_path=default_config_path)


def test_opacity_above_max_raises_config_error_RT2_12(default_config_path, user_config):
    """RT-2.12: opacity > 1.0 raises ConfigError."""
    path = user_config({"display": {"opacity": 1.5}})
    with pytest.raises(ConfigError, match="opacity"):
        load_config(user_config_path=path, default_config_path=default_config_path)


def test_opacity_below_min_raises_config_error_RT2_13(default_config_path, user_config):
    """RT-2.13: opacity < 0.0 raises ConfigError."""
    path = user_config({"display": {"opacity": -0.1}})
    with pytest.raises(ConfigError, match="opacity"):
        load_config(user_config_path=path, default_config_path=default_config_path)


def test_invalid_position_raises_config_error_RT2_14(default_config_path, user_config):
    """RT-2.14: position not in {center, top, custom} raises ConfigError."""
    path = user_config({"display": {"position": "bottom-left"}})
    with pytest.raises(ConfigError, match="position"):
        load_config(user_config_path=path, default_config_path=default_config_path)


def test_zero_width_raises_config_error_RT2_15(default_config_path, user_config):
    """RT-2.15: width <= 0 raises ConfigError."""
    path = user_config({"display": {"width": 0}})
    with pytest.raises(ConfigError, match="display.width"):
        load_config(user_config_path=path, default_config_path=default_config_path)


def test_negative_height_raises_config_error_RT2_16(default_config_path, user_config):
    """RT-2.16: height <= 0 raises ConfigError."""
    path = user_config({"display": {"height": -5}})
    with pytest.raises(ConfigError, match="display.height"):
        load_config(user_config_path=path, default_config_path=default_config_path)
