# ABOUTME: Bundled font loading for fzfLAUNCHER.
# ABOUTME: Loads Fzfira Code from resources/fonts/, falls back to system fixed font.

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QFontDatabase

logger = logging.getLogger(__name__)

_FONT_DIR = Path(__file__).parent.parent.parent / "resources" / "fonts"
_BUNDLED_FAMILY = "Fzfira Code"


def load_bundled_font(font_dir: Path = _FONT_DIR) -> str:
    """Load the Fzfira Code TTF from font_dir.

    Returns the family name "Fzfira Code" on success, or the system fixed
    font family name if no TTF files are found in font_dir.
    """
    ttf_files = sorted(font_dir.glob("*.ttf")) if font_dir.is_dir() else []

    loaded = False
    for ttf in ttf_files:
        font_id = QFontDatabase.addApplicationFont(str(ttf))
        if font_id >= 0:
            loaded = True
            logger.debug("Loaded font: %s (id=%d)", ttf.name, font_id)
        else:
            logger.warning("Failed to load font: %s", ttf.name)

    if loaded:
        return _BUNDLED_FAMILY

    fallback = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()
    logger.info(
        "Fzfira Code not found in %s; using system font: %s", font_dir, fallback
    )
    return fallback
