# ABOUTME: Terminal widget that embeds fzf via a pseudo-terminal.
# ABOUTME: Uses pty.fork() for proper controlling terminal setup and pyte for rendering.

from __future__ import annotations

import fcntl
import logging
import os
import pty
import select as sel
import shutil
import signal
import struct
import termios

import pyte
from PySide6.QtCore import QSocketNotifier, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class TerminalWidget(QWidget):
    """Widget that hosts fzf in a pseudo-terminal and renders its output via pyte."""

    selection_made = Signal(str)
    cancelled = Signal()
    no_match = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        items: list[str],
        fzf_options: str = "",
        fzf_path: str = "fzf",
        rows: int = 20,
        cols: int = 80,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._items = items
        self._fzf_options = fzf_options
        self._fzf_path = fzf_path
        self._rows = rows
        self._cols = cols

        self._pid: int | None = None
        self._master_fd: int | None = None
        self._stdout_r: int | None = None
        self._selected_text: str | None = None
        self._exit_status: int | None = None
        self._notifier: QSocketNotifier | None = None
        self._exit_timer: QTimer | None = None

        # pyte terminal emulator
        self._screen = pyte.Screen(cols, rows)
        self._stream = pyte.ByteStream(self._screen)

        # Monospace font for rendering
        self._font = QFont("Menlo", 14)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def start(self) -> None:
        """Spawn fzf connected to a pty. Raises FileNotFoundError if fzf is missing."""
        resolved = shutil.which(self._fzf_path)
        if resolved is None and not os.path.isfile(self._fzf_path):
            raise FileNotFoundError(f"fzf binary not found: {self._fzf_path}")
        fzf_path = resolved or self._fzf_path

        # Pipes for fzf's stdin (items) and stdout (selection)
        stdin_r, stdin_w = os.pipe()
        stdout_r, stdout_w = os.pipe()

        # Build fzf command
        cmd = [fzf_path]
        if self._fzf_options:
            cmd.extend(self._fzf_options.split())

        # pty.fork() properly sets the slave as controlling terminal
        pid, master_fd = pty.fork()

        if pid == 0:
            # Child: slave pty is already stdin/stdout/stderr and ctty.
            # Replace stdin and stdout with pipes so fzf reads items from
            # the pipe and writes selection to the pipe, while using
            # /dev/tty (the slave pty) for its interactive TUI.
            os.close(stdin_w)
            os.close(stdout_r)
            os.dup2(stdin_r, 0)
            os.dup2(stdout_w, 1)
            os.close(stdin_r)
            os.close(stdout_w)
            try:
                os.execvp(cmd[0], cmd)
            except OSError:
                os._exit(127)

        # Parent
        os.close(stdin_r)
        os.close(stdout_w)

        self._pid = pid
        self._master_fd = master_fd
        self._stdout_r = stdout_r

        # Set terminal size on the pty
        winsize = struct.pack("HHHH", self._rows, self._cols, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)

        # Write items to fzf's stdin pipe, then close to signal EOF
        items_text = "\n".join(self._items) + "\n"
        os.write(stdin_w, items_text.encode())
        os.close(stdin_w)

        # Async read from pty master via Qt event loop
        self._notifier = QSocketNotifier(master_fd, QSocketNotifier.Type.Read, self)
        self._notifier.activated.connect(self._read_pty)

        # Poll for fzf exit
        self._exit_timer = QTimer(self)
        self._exit_timer.timeout.connect(self._check_exit)
        self._exit_timer.start(50)

    def _read_pty(self) -> None:
        """Read available data from the pty master and feed into pyte."""
        try:
            data = os.read(self._master_fd, 65536)
            if data:
                self._stream.feed(data)
                self.update()
        except OSError:
            pass

    def _check_exit(self) -> None:
        """Poll whether fzf has exited via waitpid."""
        if self._pid is None:
            return
        try:
            wpid, status = os.waitpid(self._pid, os.WNOHANG)
        except ChildProcessError:
            self._exit_timer.stop()
            return
        if wpid == 0:
            return
        self._exit_timer.stop()
        if self._notifier is not None:
            self._notifier.setEnabled(False)
        self._drain_pty()
        if os.WIFEXITED(status):
            retcode = os.WEXITSTATUS(status)
        elif os.WIFSIGNALED(status):
            retcode = -os.WTERMSIG(status)
        else:
            retcode = -1
        self._handle_exit(retcode)

    def _drain_pty(self) -> None:
        """Read any remaining data from the pty after fzf exits."""
        if self._master_fd is None:
            return
        while True:
            ready, _, _ = sel.select([self._master_fd], [], [], 0.05)
            if not ready:
                break
            try:
                data = os.read(self._master_fd, 65536)
                if data:
                    self._stream.feed(data)
                else:
                    break
            except OSError:
                break

    def _handle_exit(self, retcode: int) -> None:
        """Process fzf's exit status and emit the appropriate signal."""
        self._exit_status = retcode
        if retcode == 0:
            output = self._read_stdout_pipe()
            self._selected_text = output if output else None
            if self._selected_text:
                self.selection_made.emit(self._selected_text)
            else:
                self.no_match.emit()
        elif retcode == 1:
            self.no_match.emit()
        elif retcode == 130:
            self.cancelled.emit()
        else:
            self.error_occurred.emit(f"fzf exited with code {retcode}")
        logger.info(
            "fzf exited with code %d, selection=%r", retcode, self._selected_text
        )

    def _read_stdout_pipe(self) -> str:
        """Read fzf's selection from the stdout pipe."""
        if self._stdout_r is None:
            return ""
        try:
            ready, _, _ = sel.select([self._stdout_r], [], [], 0.5)
            if ready:
                return os.read(self._stdout_r, 65536).decode().strip()
        except OSError:
            pass
        return ""

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Forward keyboard input to fzf via the pty master."""
        if self._master_fd is None:
            super().keyPressEvent(event)
            return

        key = event.key()

        # Let Escape propagate to the parent window for dismiss handling
        if key == Qt.Key.Key_Escape:
            super().keyPressEvent(event)
            return

        text = event.text()
        if text:
            self._pty_write(text.encode())
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._pty_write(b"\r")
        elif key == Qt.Key.Key_Backspace:
            self._pty_write(b"\x7f")
        elif key == Qt.Key.Key_Up:
            self._pty_write(b"\x1b[A")
        elif key == Qt.Key.Key_Down:
            self._pty_write(b"\x1b[B")

    def _pty_write(self, data: bytes) -> None:
        """Write data to the pty master fd, ignoring errors on closed fd."""
        try:
            os.write(self._master_fd, data)
        except OSError:
            pass

    def paintEvent(self, event) -> None:
        """Render the pyte screen buffer."""
        painter = QPainter(self)
        painter.setFont(self._font)
        metrics = painter.fontMetrics()
        char_h = metrics.height()

        painter.fillRect(self.rect(), QColor(0, 0, 0))
        painter.setPen(QColor(255, 255, 255))

        for row_idx, line in enumerate(self._screen.display):
            painter.drawText(0, (row_idx + 1) * char_h, line)

        painter.end()

    @property
    def screen(self) -> pyte.Screen:
        """The pyte terminal screen buffer."""
        return self._screen

    @property
    def selected_text(self) -> str | None:
        """The text selected by the user, or None."""
        return self._selected_text

    @property
    def exit_status(self) -> int | None:
        """fzf's exit code, or None if still running."""
        return self._exit_status

    @property
    def pid(self) -> int | None:
        """The fzf child process ID."""
        return self._pid

    @property
    def master_fd(self) -> int | None:
        """The pty master file descriptor."""
        return self._master_fd

    def is_running(self) -> bool:
        """Return True if the fzf process is still running."""
        if self._pid is None:
            return False
        try:
            wpid, _ = os.waitpid(self._pid, os.WNOHANG)
            return wpid == 0
        except ChildProcessError:
            return False

    def cleanup(self) -> None:
        """Clean up pty file descriptors and kill fzf if still running."""
        if self._notifier is not None:
            self._notifier.setEnabled(False)
        if self._exit_timer is not None:
            self._exit_timer.stop()
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None
        if self._stdout_r is not None:
            try:
                os.close(self._stdout_r)
            except OSError:
                pass
            self._stdout_r = None
        if self._pid is not None:
            try:
                os.kill(self._pid, signal.SIGKILL)
                os.waitpid(self._pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass
            self._pid = None
