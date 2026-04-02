# ABOUTME: PySide6 application window, lifecycle, and MVP integration.
# ABOUTME: Wires config → discovery → fzf terminal → launch dispatch.

from __future__ import annotations

import logging

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFontDatabase, QFontMetrics
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from fzflauncher.config import Config
from fzflauncher.discover import discover_applications
from fzflauncher.launch import LaunchError, launch_application
from fzflauncher.models import Target
from fzflauncher.terminal import TerminalWidget

logger = logging.getLogger(__name__)


class LauncherWindow(QMainWindow):
    """Borderless, always-on-top window that hosts the fzf terminal widget."""

    def __init__(
        self,
        config: Config,
        font_family: str | None = None,
        parent: QMainWindow | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._font_family = font_family
        self._targets: list[Target] = []
        self._terminal: TerminalWidget | None = None
        self._setup_window()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        cfg = self._config.display
        # Config width/height are terminal columns/rows — convert to pixels
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(20)
        if self._font_family:
            font.setFamily(self._font_family)
        fm = QFontMetrics(font)
        self.resize(cfg.width * fm.horizontalAdvance("W"), cfg.height * fm.height())
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

    def launch(self) -> None:
        """Run the full MVP flow: discover apps, embed fzf, handle selection."""
        cfg = self._config
        self._targets = discover_applications(
            cfg.paths.applications, cfg.paths.use_bundle_name
        )

        if not self._targets:
            logger.warning("No applications found")
            self.hide()
            QApplication.quit()
            return

        items = [t.display_name for t in self._targets]

        # Set up terminal widget as central widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self._terminal = TerminalWidget(
            items=items,
            fzf_options=cfg.fzf.options,
            rows=cfg.display.height,
            cols=cfg.display.width,
            font_family=self._font_family,
            parent=container,
        )
        layout.addWidget(self._terminal)
        self.setCentralWidget(container)

        # Connect signals
        self._terminal.selection_made.connect(self._on_selection)
        self._terminal.cancelled.connect(self._on_cancel)
        self._terminal.no_match.connect(self._on_cancel)
        self._terminal.error_occurred.connect(self._on_error)

        self._terminal.start()
        self._terminal.setFocus()

    def _on_selection(self, display_name: str) -> None:
        """Handle fzf selection: hide window, launch app."""
        self.hide()
        try:
            launch_application(display_name, self._targets)
        except LaunchError as exc:
            logger.error("Launch failed: %s", exc)
        self._quit()

    def _on_cancel(self) -> None:
        """Handle fzf cancel/no-match: hide window and quit."""
        self.hide()
        self._quit()

    def _on_error(self, message: str) -> None:
        """Handle fzf error: log and quit."""
        logger.error("fzf error: %s", message)
        self.hide()
        self._quit()

    def _quit(self) -> None:
        """Clean up and quit the application."""
        if self._terminal is not None:
            self._terminal.cleanup()
        QApplication.quit()

    def keyPressEvent(self, event: QEvent) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self._quit()
        else:
            super().keyPressEvent(event)

    def event(self, event: QEvent) -> bool:  # type: ignore[override]
        # WindowDeactivate is not routed to changeEvent() in Qt 6; intercept here.
        result = super().event(event)
        if event.type() == QEvent.Type.WindowDeactivate:
            self.hide()
        return result
