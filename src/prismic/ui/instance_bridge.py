"""Lets a second Prismic launch targeting an already-open collection focus
the existing window instead of just failing with a plain error.

This is a UX nicety layered on top of Phase 1's collection lock, not a
replacement for it: the lock (`persistence/lockfile.py`) is what actually
guarantees single-writer access and is authoritative. This bridge is a
best-effort local IPC channel (Qt's `QLocalServer`/`QLocalSocket`) keyed by
the collection's database path, used only to say "someone else wants this
window" — if it can't be reached for any reason, the caller falls back to
the plain locked-collection error.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

_RAISE_MESSAGE = b"raise"
_CONNECT_TIMEOUT_MS = 250


def _server_name_for(database_path: Path) -> str:
    # A hash rather than the raw path: QLocalServer names have length/
    # character restrictions that vary by platform (Windows named pipes,
    # Unix domain sockets), and a collection path can contain anything a
    # filesystem allows.
    digest = hashlib.sha256(str(database_path.resolve()).encode()).hexdigest()[:16]
    return f"prismic-{digest}"


class InstanceBridge(QObject):
    """Owns a `QLocalServer` for one collection, for as long as this
    process holds that collection open."""

    raise_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server: QLocalServer | None = None

    def take_ownership(self, database_path: Path) -> None:
        """Start listening for focus requests for `database_path`.

        Only meaningful to call after this process has already acquired
        the collection's file lock — at that point no other legitimate
        instance can own it, so any leftover local-socket file from a
        previously crashed process is safe to clear before listening.
        """
        name = _server_name_for(database_path)
        QLocalServer.removeServer(name)
        server = QLocalServer(self)
        server.newConnection.connect(self._on_new_connection)
        if server.listen(name):
            self._server = server
        # If listen() fails, focus-forwarding just won't work for this
        # collection -- a missed nicety, not a correctness problem (the
        # file lock still protects the data either way).

    def release(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None

    def _on_new_connection(self) -> None:
        assert self._server is not None
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        socket.readyRead.connect(lambda: self._on_ready_read(socket))
        socket.disconnected.connect(socket.deleteLater)

    def _on_ready_read(self, socket: QLocalSocket) -> None:
        data = bytes(socket.readAll().data())
        if data == _RAISE_MESSAGE:
            self.raise_requested.emit()
        socket.disconnectFromServer()


def request_focus(database_path: Path, timeout_ms: int = _CONNECT_TIMEOUT_MS) -> bool:
    """Ask whichever process owns `database_path` (if any) to focus its
    window. Returns True if the request was actually delivered."""
    name = _server_name_for(database_path)
    socket = QLocalSocket()
    socket.connectToServer(name)
    try:
        if not socket.waitForConnected(timeout_ms):
            return False
        socket.write(_RAISE_MESSAGE)
        socket.waitForBytesWritten(timeout_ms)
        socket.disconnectFromServer()
        return True
    finally:
        socket.deleteLater()
