"""Application bootstrap and main entry point."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

from netcatcher.gui.main_window import MainWindow

_style_dir = Path(__file__).parent / "resources" / "styles"
_app_instance: QApplication | None = None


def _build_palette(theme: str) -> QPalette:
    """Build a fully-specified palette for the given theme."""
    pal = QPalette()

    if theme == "dark":
        bg       = QColor("#1e1e2e")
        surface  = QColor("#181825")
        text     = QColor("#cdd6f4")
        dim      = QColor("#a6adc8")
        btn      = QColor("#313244")
        border   = QColor("#313244")
        sel      = QColor("#45475a")
        link     = QColor("#89b4fa")
        deep     = QColor("#11111b")

        for grp in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
            pal.setColor(grp, QPalette.ColorRole.Window,          surface)
            pal.setColor(grp, QPalette.ColorRole.WindowText,      text)
            pal.setColor(grp, QPalette.ColorRole.Base,            bg)
            pal.setColor(grp, QPalette.ColorRole.AlternateBase,   QColor("#242437"))
            pal.setColor(grp, QPalette.ColorRole.ToolTipBase,     bg)
            pal.setColor(grp, QPalette.ColorRole.ToolTipText,     text)
            pal.setColor(grp, QPalette.ColorRole.Text,            text)
            pal.setColor(grp, QPalette.ColorRole.Button,          btn)
            pal.setColor(grp, QPalette.ColorRole.ButtonText,      text)
            pal.setColor(grp, QPalette.ColorRole.BrightText,      text)
            pal.setColor(grp, QPalette.ColorRole.Link,            link)
            pal.setColor(grp, QPalette.ColorRole.LinkVisited,     link)
            pal.setColor(grp, QPalette.ColorRole.Highlight,       sel)
            pal.setColor(grp, QPalette.ColorRole.HighlightedText, text)
            pal.setColor(grp, QPalette.ColorRole.PlaceholderText, QColor("#6c7086"))
            # 3D bevel / separator colors
            pal.setColor(grp, QPalette.ColorRole.Light,           QColor("#313244"))
            pal.setColor(grp, QPalette.ColorRole.Midlight,        QColor("#292940"))
            pal.setColor(grp, QPalette.ColorRole.Mid,             border)
            pal.setColor(grp, QPalette.ColorRole.Dark,            deep)
            pal.setColor(grp, QPalette.ColorRole.Shadow,          deep)
    else:
        bg       = QColor("#ffffff")
        surface  = QColor("#eff1f5")
        text     = QColor("#4c4f69")
        dim      = QColor("#5c5f77")
        btn      = QColor("#ccd0da")
        border   = QColor("#ccd0da")
        sel      = QColor("#ccd0da")
        link     = QColor("#1e66f5")

        for grp in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
            pal.setColor(grp, QPalette.ColorRole.Window,          surface)
            pal.setColor(grp, QPalette.ColorRole.WindowText,      text)
            pal.setColor(grp, QPalette.ColorRole.Base,            bg)
            pal.setColor(grp, QPalette.ColorRole.AlternateBase,   QColor("#f2f3f7"))
            pal.setColor(grp, QPalette.ColorRole.ToolTipBase,     bg)
            pal.setColor(grp, QPalette.ColorRole.ToolTipText,     text)
            pal.setColor(grp, QPalette.ColorRole.Text,            text)
            pal.setColor(grp, QPalette.ColorRole.Button,          btn)
            pal.setColor(grp, QPalette.ColorRole.ButtonText,      text)
            pal.setColor(grp, QPalette.ColorRole.BrightText,      text)
            pal.setColor(grp, QPalette.ColorRole.Link,            link)
            pal.setColor(grp, QPalette.ColorRole.LinkVisited,     link)
            pal.setColor(grp, QPalette.ColorRole.Highlight,       sel)
            pal.setColor(grp, QPalette.ColorRole.HighlightedText, text)
            pal.setColor(grp, QPalette.ColorRole.PlaceholderText, QColor("#9ca0b0"))
            pal.setColor(grp, QPalette.ColorRole.Light,           QColor("#ffffff"))
            pal.setColor(grp, QPalette.ColorRole.Midlight,        QColor("#e6e9ef"))
            pal.setColor(grp, QPalette.ColorRole.Mid,             border)
            pal.setColor(grp, QPalette.ColorRole.Dark,            QColor("#bcc0cc"))
            pal.setColor(grp, QPalette.ColorRole.Shadow,          QColor("#acb0be"))

    return pal


def load_theme(theme: str = "dark"):
    """Load a theme stylesheet by name ('dark' or 'light')."""
    if _app_instance is None:
        return

    # 1. Build and set the palette FIRST so it's ready before stylesheet applies
    pal = _build_palette(theme)
    _app_instance.setPalette(pal)

    # 2. Clear then re-apply stylesheet to force a complete style reparse
    path = _style_dir / f"{theme}.qss"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            qss = f.read()
        _app_instance.setStyleSheet("")       # clear old styles
        _app_instance.setStyleSheet(qss)      # apply new styles


def main():
    global _app_instance
    app = QApplication(sys.argv)
    _app_instance = app
    app.setApplicationName("NetCatcher")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("NetCatcher")

    app.setStyle("Fusion")

    # Apply initial theme before creating any widgets
    from netcatcher.config.settings import Settings
    initial_settings = Settings()
    load_theme(initial_settings.theme)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
