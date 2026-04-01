# ABOUTME: Core data models shared across fzfLAUNCHER modules.
# ABOUTME: Defines Target and TargetType used throughout discovery and launch.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any


class TargetType(Enum):
    APPLICATION = auto()


@dataclass(frozen=True)
class Target:
    type: TargetType
    display_name: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)
