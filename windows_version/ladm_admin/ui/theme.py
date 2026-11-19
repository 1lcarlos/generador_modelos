"""Tema visual: paleta de colores (claro/oscuro) y hoja de estilos Qt."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette


@dataclass(frozen=True)
class Tokens:
    bg: str
    surface: str
    surface_alt: str
    sidebar: str
    sidebar_text: str
    sidebar_active: str
    border: str
    text: str
    text_muted: str
    primary: str
    primary_hover: str
    primary_text: str
    success: str
    warning: str
    error: str
    info: str
    selection: str
    log_bg: str
    log_text: str


LIGHT = Tokens(
    bg="#f4f6f9", surface="#ffffff", surface_alt="#f8fafc", sidebar="#13294b", sidebar_text="#c9d4e5",
    sidebar_active="#2b4c7e", border="#d9dee7", text="#1c2433", text_muted="#5f6b7d",
    primary="#1d5fbf", primary_hover="#174e9e", primary_text="#ffffff",
    success="#1e7f4f", warning="#b26a00", error="#c0352b", info="#1d5fbf",
    selection="#dbe7fb", log_bg="#fbfcfe", log_text="#2a3342",
)

DARK = Tokens(
    bg="#14181f", surface="#1c222b", surface_alt="#222934", sidebar="#0e1218", sidebar_text="#9eabbe",
    sidebar_active="#24324a", border="#323b48", text="#e3e8ef", text_muted="#97a3b4",
    primary="#4c8df0", primary_hover="#6aa1f3", primary_text="#0b1220",
    success="#4cc38a", warning="#f0a43c", error="#f0675c", info="#6aa1f3",
    selection="#2a3d5c", log_bg="#161b22", log_text="#cfd7e3",
)

_current: Tokens = LIGHT


def tokens() -> Tokens:
    return _current


def system_prefers_dark() -> bool:
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:  # pragma: no cover
        return False


def resolve(mode: str) -> Tokens:
    if mode == "oscuro":
        return DARK
    if mode == "claro":
        return LIGHT
    return DARK if system_prefers_dark() else LIGHT


def apply(app, mode: str = "sistema") -> Tokens:
    global _current
    t = resolve(mode)
    _current = t
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(t.bg))
    pal.setColor(QPalette.WindowText, QColor(t.text))
    pal.setColor(QPalette.Base, QColor(t.surface))
    pal.setColor(QPalette.AlternateBase, QColor(t.surface_alt))
    pal.setColor(QPalette.Text, QColor(t.text))
    pal.setColor(QPalette.Button, QColor(t.surface))
    pal.setColor(QPalette.ButtonText, QColor(t.text))
    pal.setColor(QPalette.Highlight, QColor(t.primary))
    pal.setColor(QPalette.HighlightedText, QColor(t.primary_text))
    pal.setColor(QPalette.ToolTipBase, QColor(t.surface))
    pal.setColor(QPalette.ToolTipText, QColor(t.text))
    pal.setColor(QPalette.PlaceholderText, QColor(t.text_muted))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(t.text_muted))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(t.text_muted))
    app.setPalette(pal)
    app.setStyleSheet(stylesheet(t))
    return t


def stylesheet(t: Tokens) -> str:
    return f"""
    QWidget {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: 10pt; color: {t.text}; }}
    QMainWindow, QDialog {{ background: {t.bg}; }}

    /* ---------- barra lateral ---------- */
    #Sidebar {{ background: {t.sidebar}; }}
    #Sidebar QLabel#Brand {{ color: #ffffff; font-size: 12pt; font-weight: 600; }}
    #Sidebar QLabel#BrandSub {{ color: {t.sidebar_text}; font-size: 8.5pt; }}
    #Sidebar QLabel#NavSection {{ color: {t.sidebar_text}; font-size: 8pt; font-weight: 600;
                                  letter-spacing: 1px; padding: 14px 18px 4px 18px; }}
    #NavList {{ background: transparent; border: none; outline: 0; }}
    #NavList::item {{ color: {t.sidebar_text}; padding: 9px 14px; margin: 1px 8px; border-radius: 6px; }}
    #NavList::item:hover {{ background: rgba(255,255,255,0.06); color: #ffffff; }}
    #NavList::item:selected {{ background: {t.sidebar_active}; color: #ffffff; font-weight: 600; }}
    #Sidebar QLabel#Version {{ color: {t.sidebar_text}; font-size: 8pt; }}

    /* ---------- encabezado ---------- */
    #Header {{ background: {t.surface}; border-bottom: 1px solid {t.border}; }}
    #Header QLabel#PageTitle {{ font-size: 14pt; font-weight: 600; }}
    #Header QLabel#PageSubtitle {{ color: {t.text_muted}; }}
    QLabel#ContextLabel {{ color: {t.text_muted}; font-size: 8.5pt; }}

    /* ---------- tarjetas y secciones ---------- */
    QFrame#Card {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 8px; }}
    QLabel#CardTitle {{ font-size: 11pt; font-weight: 600; }}
    QLabel#StepNumber {{ background: {t.primary}; color: {t.primary_text}; border-radius: 12px;
                         min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px;
                         qproperty-alignment: AlignCenter; font-weight: 600; }}
    QLabel#Muted, QLabel#Hint {{ color: {t.text_muted}; }}
    QLabel#Hint {{ font-size: 9pt; }}
    QFrame#Banner {{ border-radius: 6px; padding: 2px; }}
    QFrame#Banner[kind="warning"] {{ background: rgba(178,106,0,0.10); border: 1px solid {t.warning}; }}
    QFrame#Banner[kind="error"] {{ background: rgba(192,53,43,0.10); border: 1px solid {t.error}; }}
    QFrame#Banner[kind="info"] {{ background: rgba(29,95,191,0.08); border: 1px solid {t.info}; }}
    QFrame#Banner[kind="success"] {{ background: rgba(30,127,79,0.10); border: 1px solid {t.success}; }}

    /* ---------- controles ---------- */
    QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox {{
        background: {t.surface}; border: 1px solid {t.border}; border-radius: 6px; padding: 5px 8px;
        selection-background-color: {t.primary}; selection-color: {t.primary_text};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {t.primary}; }}
    QLineEdit:disabled, QComboBox:disabled {{ color: {t.text_muted}; background: {t.surface_alt}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{ background: {t.surface}; border: 1px solid {t.border};
                                   selection-background-color: {t.selection}; selection-color: {t.text}; }}

    QPushButton {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 6px;
                   padding: 6px 14px; min-height: 18px; }}
    QPushButton:hover {{ border-color: {t.primary}; }}
    QPushButton:pressed {{ background: {t.selection}; }}
    QPushButton:disabled {{ color: {t.text_muted}; background: {t.surface_alt}; }}
    QPushButton[variant="primary"] {{ background: {t.primary}; color: {t.primary_text}; border: 1px solid {t.primary};
                                      font-weight: 600; padding: 7px 20px; }}
    QPushButton[variant="primary"]:hover {{ background: {t.primary_hover}; }}
    QPushButton[variant="primary"]:disabled {{ background: {t.border}; border-color: {t.border}; color: {t.text_muted}; }}
    QPushButton[variant="danger"] {{ color: {t.error}; border-color: {t.error}; }}
    QPushButton[variant="danger"]:hover {{ background: rgba(192,53,43,0.08); }}
    QPushButton[variant="link"] {{ border: none; background: transparent; color: {t.primary}; padding: 2px 4px; }}
    QPushButton[variant="link"]:hover {{ text-decoration: underline; }}
    QToolButton {{ border: none; border-radius: 4px; padding: 3px; }}
    QToolButton:hover {{ background: {t.selection}; }}

    QCheckBox, QRadioButton {{ spacing: 8px; }}
    QGroupBox {{ border: 1px solid {t.border}; border-radius: 8px; margin-top: 14px; padding: 12px 10px 10px 10px;
                 background: {t.surface}; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; font-weight: 600; }}

    /* ---------- tablas ---------- */
    QTableView, QTreeView, QListWidget {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 6px;
                              gridline-color: {t.border}; alternate-background-color: {t.surface_alt};
                              selection-background-color: {t.selection}; selection-color: {t.text}; }}
    QHeaderView::section {{ background: {t.surface_alt}; border: none; border-bottom: 1px solid {t.border};
                            border-right: 1px solid {t.border}; padding: 6px 8px; font-weight: 600; color: {t.text_muted}; }}
    QTableView::item {{ padding: 4px 6px; }}
    QListWidget::item {{ padding: 6px 8px; }}
    QListWidget::item:selected {{ background: {t.selection}; color: {t.text}; }}

    QTabWidget::pane {{ border: 1px solid {t.border}; border-radius: 6px; background: {t.surface}; top: -1px; }}
    QTabBar::tab {{ background: transparent; padding: 7px 14px; border: none; color: {t.text_muted}; }}
    QTabBar::tab:selected {{ color: {t.primary}; border-bottom: 2px solid {t.primary}; font-weight: 600; }}
    QTabBar::tab:hover {{ color: {t.text}; }}

    QProgressBar {{ background: {t.surface_alt}; border: 1px solid {t.border}; border-radius: 5px; height: 10px;
                    text-align: center; font-size: 8pt; color: {t.text_muted}; }}
    QProgressBar::chunk {{ background: {t.primary}; border-radius: 4px; }}

    QPlainTextEdit#Log {{ background: {t.log_bg}; color: {t.log_text}; font-family: "Cascadia Mono", "Consolas", monospace;
                          font-size: 9pt; border-radius: 6px; }}
    QSplitter::handle {{ background: transparent; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QStatusBar {{ background: {t.surface}; border-top: 1px solid {t.border}; color: {t.text_muted}; }}
    QToolTip {{ border: 1px solid {t.border}; padding: 6px; }}
    QMenu {{ background: {t.surface}; border: 1px solid {t.border}; padding: 4px; }}
    QMenu::item {{ padding: 6px 18px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {t.selection}; color: {t.text}; }}
    """
