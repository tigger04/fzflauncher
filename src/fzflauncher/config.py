# ABOUTME: Configuration loading, validation, and immutable Config dataclass.
# ABOUTME: Merges config/default.yaml with ~/.config/fzflauncher/config.yaml.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when configuration is invalid or cannot be loaded."""


_VALID_POSITIONS = frozenset({"center", "top", "custom"})
_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "default.yaml"
_USER_CONFIG_PATH = Path.home() / ".config" / "fzflauncher" / "config.yaml"


@dataclass(frozen=True)
class PathsConfig:
    applications: tuple[str, ...]
    use_bundle_name: bool


@dataclass(frozen=True)
class DisplayConfig:
    width: int
    height: int
    opacity: float
    position: str
    x_offset: int
    y_offset: int


@dataclass(frozen=True)
class FzfConfig:
    options: str


@dataclass(frozen=True)
class HotkeyConfig:
    global_hotkey: str  # mapped from YAML key 'global' (Python reserved word)


@dataclass(frozen=True)
class Config:
    paths: PathsConfig
    display: DisplayConfig
    fzf: FzfConfig
    hotkey: HotkeyConfig


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base, returning a new dict."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _expand_paths(paths: list[str]) -> tuple[str, ...]:
    """Expand ~ in path strings to absolute paths."""
    return tuple(str(Path(p).expanduser()) for p in paths)


def _validate(raw: dict[str, Any]) -> None:
    """Validate raw merged config dict; raise ConfigError with field name on any violation."""
    display = raw.get("display", {})

    opacity = display.get("opacity")
    if not isinstance(opacity, (int, float)):
        raise ConfigError(
            f"display.opacity must be a number, got {type(opacity).__name__!r}"
        )
    if not 0.0 <= float(opacity) <= 1.0:
        raise ConfigError(f"display.opacity must be between 0.0 and 1.0, got {opacity}")

    position = display.get("position")
    if not isinstance(position, str):
        raise ConfigError(
            f"display.position must be a string, got {type(position).__name__!r}"
        )
    if position not in _VALID_POSITIONS:
        raise ConfigError(
            f"display.position must be one of {sorted(_VALID_POSITIONS)}, got {position!r}"
        )

    width = display.get("width")
    if not isinstance(width, int) or isinstance(width, bool):
        raise ConfigError(
            f"display.width must be an integer, got {type(width).__name__!r}"
        )
    if width <= 0:
        raise ConfigError(f"display.width must be positive, got {width}")

    height = display.get("height")
    if not isinstance(height, int) or isinstance(height, bool):
        raise ConfigError(
            f"display.height must be an integer, got {type(height).__name__!r}"
        )
    if height <= 0:
        raise ConfigError(f"display.height must be positive, got {height}")


def _build(raw: dict[str, Any]) -> Config:
    """Construct an immutable Config from a validated raw dict."""
    paths_raw = raw["paths"]
    display_raw = raw["display"]

    paths = PathsConfig(
        applications=_expand_paths(paths_raw["applications"]),
        use_bundle_name=bool(paths_raw["use_bundle_name"]),
    )
    display = DisplayConfig(
        width=int(display_raw["width"]),
        height=int(display_raw["height"]),
        opacity=float(display_raw["opacity"]),
        position=str(display_raw["position"]),
        x_offset=int(display_raw.get("x_offset", 0)),
        y_offset=int(display_raw.get("y_offset", 0)),
    )
    fzf = FzfConfig(options=str(raw["fzf"]["options"]))
    hotkey = HotkeyConfig(global_hotkey=str(raw["hotkey"]["global"]))

    return Config(paths=paths, display=display, fzf=fzf, hotkey=hotkey)


def load_config(
    user_config_path: Path | None = None,
    default_config_path: Path | None = None,
) -> Config:
    """Load, merge, validate, and return an immutable Config.

    Loads config/default.yaml, then deep-merges user config over it if present.
    Expands ~ in all path values. Validates all fields before returning.

    Args:
        user_config_path: Path to user config YAML.
            Defaults to ~/.config/fzflauncher/config.yaml.
        default_config_path: Path to default config YAML.
            Defaults to the bundled config/default.yaml.

    Raises:
        ConfigError: If any configuration value is invalid or YAML is malformed.
    """
    if default_config_path is None:
        default_config_path = _DEFAULT_CONFIG_PATH
    if user_config_path is None:
        user_config_path = _USER_CONFIG_PATH

    try:
        with open(default_config_path) as f:
            raw: dict[str, Any] = yaml.safe_load(f)
    except FileNotFoundError as exc:
        raise ConfigError(f"Default config not found: {default_config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in default config: {exc}") from exc

    if user_config_path.exists():
        try:
            with open(user_config_path) as f:
                user_raw = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise ConfigError(
                f"Invalid YAML in user config {user_config_path}: {exc}"
            ) from exc

        if user_raw is not None:
            raw = _deep_merge(raw, user_raw)

    _validate(raw)
    return _build(raw)
