"""Application settings management using QSettings."""

from PyQt6.QtCore import QSettings

from netcatcher.config.constants import (
    DEFAULT_CAPTURE_BUFFER_SIZE,
    DEFAULT_MITM_PORT,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
)


class Settings:
    """Wraps QSettings for type-safe access to application preferences."""

    def __init__(self):
        self._settings = QSettings()

    @property
    def buffer_size(self) -> int:
        return self._settings.value("capture/buffer_size", DEFAULT_CAPTURE_BUFFER_SIZE, type=int)

    @buffer_size.setter
    def buffer_size(self, value: int):
        self._settings.setValue("capture/buffer_size", value)

    @property
    def mitm_port(self) -> int:
        return self._settings.value("capture/mitm_port", DEFAULT_MITM_PORT, type=int)

    @mitm_port.setter
    def mitm_port(self, value: int):
        self._settings.setValue("capture/mitm_port", value)

    @property
    def capture_interface(self) -> str:
        return self._settings.value("capture/interface", "", type=str)

    @capture_interface.setter
    def capture_interface(self, value: str):
        self._settings.setValue("capture/interface", value)

    @property
    def window_geometry(self) -> bytes:
        return self._settings.value("window/geometry", b"")

    @window_geometry.setter
    def window_geometry(self, data: bytes):
        self._settings.setValue("window/geometry", data)

    @property
    def window_state(self) -> bytes:
        return self._settings.value("window/state", b"")

    @window_state.setter
    def window_state(self, data: bytes):
        self._settings.setValue("window/state", data)

    @property
    def splitter_state(self) -> bytes:
        return self._settings.value("window/splitter", b"")

    @splitter_state.setter
    def splitter_state(self, data: bytes):
        self._settings.setValue("window/splitter", data)

    @property
    def last_export_dir(self) -> str:
        return self._settings.value("export/last_directory", "", type=str)

    @last_export_dir.setter
    def last_export_dir(self, value: str):
        self._settings.setValue("export/last_directory", value)

    @property
    def mitm_enabled(self) -> bool:
        return self._settings.value("capture/mitm_enabled", False, type=bool)

    @mitm_enabled.setter
    def mitm_enabled(self, value: bool):
        self._settings.setValue("capture/mitm_enabled", value)

    @property
    def theme(self) -> str:
        return self._settings.value("appearance/theme", "dark", type=str)

    @theme.setter
    def theme(self, value: str):
        self._settings.setValue("appearance/theme", value)
