# ABOUTME: PySide6 application window and lifecycle management.
# ABOUTME: Borderless, floating, always-on-top launcher window with show/hide lifecycle.

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QMainWindow

from fzflauncher.config import Config


class LauncherWindow(QMainWindow):
    """Borderless, always-on-top window that hosts the fzf terminal widget."""

    def __init__(self, config: Config, parent: QMainWindow | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._setup_window()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        cfg = self._config.display
        self.resize(cfg.width, cfg.height)
        self.setWindowOpacity(cfg.opacity)
        if cfg.position == "center":
            self._center_on_screen()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.geometry()
        x = (geo.width() - self.width()) // 2 + geo.x()
        y = (geo.height() - self.height()) // 2 + geo.y()
        self.move(x, y)

    def keyPressEvent(self, event: QEvent) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def event(self, event: QEvent) -> bool:  # type: ignore[override]
        # WindowDeactivate is not routed to changeEvent() in Qt 6; intercept here.
        result = super().event(event)
        if event.type() == QEvent.Type.WindowDeactivate:
            self.hide()
        return result
