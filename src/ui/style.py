# -*- coding: utf-8 -*-
MODERN_THEME_STYLESHEET = """
QWidget { background-color: #1e1e20; color: #e0e0e0; font-family: "Segoe UI", sans-serif; font-size: 11px; }
QGroupBox { border: 1px solid #333337; border-radius: 6px; margin-top: 12px; padding-top: 15px; font-weight: bold; color: #888888; background-color: #242426; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; background-color: #242426; }
QPushButton { background-color: #38383c; border: 1px solid #4a4a4e; border-radius: 4px; color: #ffffff; min-height: 26px; padding: 0px 15px; text-align: center; outline: none; qproperty-cursor: pointingHand; }
QPushButton:hover { background-color: #48484c; border: 1px solid #007acc; }
QPushButton:pressed { background-color: #007acc; border: 1px solid #005f9e; }
QPushButton:checked { background-color: #007acc; border: 1px solid #005f9e; color: white; font-weight: bold; }
QPushButton:disabled { background-color: #2a2a2c; color: #666666; border: 1px solid #333333; }
QPushButton#btnImport { background-color: #007acc; color: white; font-weight: bold; font-size: 14px; min-height: 42px; border-radius: 6px; border: none; }
QPushButton#btnImport:hover { background-color: #008be6; }
QPushButton#btnImport:disabled { background-color: #2a2a2c; color: #555; }
QPushButton#btnRelink { background-color: #5a8a5a; font-weight: bold; font-size: 12px; min-height: 32px; }
QPushButton#btnRelink:hover { background-color: #6a9a6a; }
QPushButton#btnStrip { background-color: #a84a4a; font-weight: bold; min-height: 28px; }
QPushButton#btnStrip:hover { background-color: #b85a5a; }
QPushButton#btnUNC { background-color: #4a6a8a; font-weight: bold; min-height: 28px; }
QPushButton#btnUNC:hover { background-color: #5a7a9a; }
QPushButton#btnScan { background-color: #d67b22; font-weight: bold; min-height: 32px; }
QPushButton#btnScan:hover { background-color: #e68b32; }
QLineEdit, QComboBox { background-color: #18181a; border: 1px solid #3e3e42; border-radius: 4px; padding: 6px; color: white; min-height: 18px; }
QScrollBar:vertical { border: none; background-color: #18181a; width: 10px; margin: 0px 0px 0px 0px; border-radius: 5px; }
QScrollBar::handle:vertical { background-color: #4a4a4e; min-height: 30px; border-radius: 5px; }
QScrollBar::handle:vertical:hover { background-color: #6a6a6e; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal { border: none; background-color: #18181a; height: 10px; margin: 0px 0px 0px 0px; border-radius: 5px; }
QScrollBar::handle:horizontal { background-color: #4a4a4e; min-width: 30px; border-radius: 5px; }
QScrollBar::handle:horizontal:hover { background-color: #6a6a6e; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { border: none; background: none; width: 0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QListWidget { background-color: #18181a; border: 1px solid #333337; border-radius: 6px; padding: 5px; outline: none; }
QListWidget::item { background-color: #252528; border-radius: 4px; margin: 2px; }
QListWidget::item:selected { background-color: #3a3a40; border: 1px solid #007acc; }
QListWidget::item:hover { background-color: #303035; border: 1px solid #555; }
QTableWidget { background-color: #18181a; border: 1px solid #333337; border-radius: 6px; color: #e0e0e0; outline: none; }
QTableWidget::item:selected { background-color: #333337; border: 1px solid #007acc; }
QHeaderView::section { background-color: #2a2a2c; color: #888; padding: 6px; border: 1px solid #333337; font-weight: bold; }
QProgressBar { border: 1px solid #333337; border-radius: 6px; background-color: #18181a; text-align: center; color: white; font-weight: bold; min-height: 22px; }
QProgressBar::chunk { background-color: #007acc; border-radius: 5px; }
QProgressBar#pbRelink::chunk { background-color: #5a8a5a; }
QCheckBox { spacing: 8px; font-size: 12px; }
QCheckBox::indicator { width: 16px; height: 16px; background-color: #18181a; border: 1px solid #555555; border-radius: 4px; }
QCheckBox::indicator:hover { border: 1px solid #007acc; }
QCheckBox::indicator:checked { background-color: #007acc; border: 1px solid #005f9e; }
QMenu { background-color: #252528; border: 1px solid #444; padding: 5px; border-radius: 4px; }
QMenu::item { padding: 6px 25px; color: #e0e0e0; border-radius: 3px; }
QMenu::item:selected { background-color: #007acc; color: white; }
QTabWidget::pane { border: 1px solid #333337; background-color: #1e1e20; border-radius: 6px; top: -1px; }
QTabBar::tab { background-color: #2a2a2c; color: #888; padding: 10px 18px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; border: 1px solid #333337; border-bottom: none; }
QTabBar::tab:selected { background-color: #1e1e20; color: #007acc; font-weight: bold; border-bottom: 1px solid #1e1e20; }
QTabBar::tab:hover:!selected { background-color: #38383c; }
QLabel#lblHelp { color: #666; font-style: italic; font-size: 10px; }

/* Toast Notification */
#ToastWidget { background-color: rgba(30, 30, 32, 230); border: 1px solid #007acc; border-radius: 8px; }
#ToastLabel { color: #ffffff; font-size: 12px; font-weight: bold; padding: 10px; }
"""
