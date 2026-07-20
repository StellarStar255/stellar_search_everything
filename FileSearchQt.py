"""Stellar Search Everything — PySide6 版本。

从 Tkinter 版（FileSearchGUI.py）迁移：搜索逻辑原样移植，UI 用 Qt 重写。
配置文件（~/.file_search_config.json）与 Tk 版完全兼容。
"""
import os
import re
import sys
import json
import time
import datetime
import tempfile
import subprocess
import threading
import urllib.request

from PySide6.QtCore import (Qt, QObject, Signal, QUrl, QMimeData,
                            QAbstractTableModel, QModelIndex, QTimer, QEvent)
from PySide6.QtGui import (QIcon, QAction, QActionGroup, QFont, QKeySequence,
                           QShortcut, QColor, QBrush)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QComboBox, QPushButton,
    QRadioButton, QCheckBox, QHBoxLayout, QVBoxLayout, QGridLayout,
    QTableView, QMenu, QFileDialog, QMessageBox,
    QHeaderView, QFrame, QAbstractItemView, QButtonGroup, QSystemTrayIcon,
)

from translations import TRANSLATIONS

APP_VERSION = "1.6.2"
GITHUB_REPO = "StellarStar255/stellar_search_everything"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def version_tuple(s):
    """'v1.4.0' / '1.4.0' → (1, 4, 0)，用于版本比较"""
    nums = re.findall(r"\d+", s)
    return tuple(int(n) for n in nums[:3]) if nums else (0,)


def platform_asset_suffix():
    """当前平台对应的 Release 安装包文件名后缀"""
    if sys.platform == "darwin":
        return ".dmg"
    if sys.platform.startswith("win"):
        return "-setup.exe"
    return ".deb"


def https_context():
    """打包后的 Python 没有系统 CA 证书（SSL: CERTIFICATE_VERIFY_FAILED），
    用 certifi 自带的证书链；certifi 不可用时退回默认行为"""
    try:
        import ssl
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


LAUNCH_LOG = os.path.join(os.path.expanduser("~"), ".stellar_search_everything.log")


def setup_launch_log():
    """打包运行时把 stderr 重定向到 ~/.stellar_search_everything.log。
    从桌面图标启动的应用没有终端，Qt 平台插件缺库、原生崩溃等致命错误
    全部输出到看不见的 stderr——落盘后才有排查依据。终端里运行则不重定向。"""
    if not getattr(sys, "frozen", False):
        return
    try:
        try:
            if os.path.getsize(LAUNCH_LOG) > 1024 * 1024:
                os.remove(LAUNCH_LOG)
        except OSError:
            pass
        f = open(LAUNCH_LOG, "a", buffering=1, encoding="utf-8", errors="replace")
        f.write(f"\n--- 启动 v{APP_VERSION} "
                f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} "
                f"platform={sys.platform} exe={sys.executable} ---\n")
        interactive = False
        try:
            interactive = sys.stderr is not None and sys.stderr.isatty()
        except Exception:
            pass
        if not interactive:
            os.dup2(f.fileno(), 2)   # 原生层（Qt/qFatal）的 stderr 也进日志
            sys.stderr = f
        import faulthandler
        faulthandler.enable(file=f)  # 段错误时把各线程栈写进日志
    except Exception:
        pass


def resource_path(relative_path):
    """获取资源文件的绝对路径（兼容打包后的应用）"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)


# 项目暗色主题配色（与 Tk 版一致）
BG = "#1e1f22"
SURFACE = "#2b2d31"
ENTRY_BG = "#313338"
STRIPE_BG = "#36393f"
BORDER = "#3f4147"
ACCENT = "#4e8cff"
ACCENT_HOVER = "#6ba1ff"
ACCENT_PRESSED = "#3d74d9"
TEXT = "#e8eaed"
MUTED = "#9aa0a6"
BUTTON_BG = "#3a3d42"
BUTTON_HOVER = "#4a4e57"
FOLDER_FG = "#8ab4f8"

QSS_TEMPLATE = """
QMainWindow, QWidget {{ background: {bg}; color: {text}; }}
#card {{ background: {surface}; border: 1px solid {border}; border-radius: 8px; }}
#card QLabel, #card QRadioButton, #card QCheckBox {{ background: {surface}; }}
QLabel#hint {{ color: {muted}; }}
QComboBox {{
    background: {entry_bg}; color: {text}; border: 1px solid {border};
    border-radius: 6px; padding: 4px 8px;
}}
QComboBox:focus {{ border-color: {accent}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {entry_bg}; color: {text};
    selection-background-color: {accent}; selection-color: #ffffff;
}}
QPushButton {{
    background: {button_bg}; color: {text}; border: none;
    border-radius: 6px; padding: 5px 16px;
}}
QPushButton:hover {{ background: {button_hover}; }}
QPushButton#accent {{ background: {accent}; color: #ffffff; }}
QPushButton#accent:hover {{ background: {accent_hover}; }}
QPushButton#accent:pressed {{ background: {accent_pressed}; }}
QPushButton#small {{ padding: 2px 8px; }}
QRadioButton, QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {border};
    border-radius: 4px; background: {entry_bg};
}}
QCheckBox::indicator:hover {{ border-color: {accent}; }}
QCheckBox::indicator:checked {{
    background: {accent}; border-color: {accent}; image: url("{check_svg}");
}}
QRadioButton::indicator {{
    width: 16px; height: 16px; border: 1px solid {border};
    border-radius: 9px; background: {entry_bg};
}}
QRadioButton::indicator:hover {{ border-color: {accent}; }}
QRadioButton::indicator:checked {{
    border-color: {accent};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 {accent}, stop:0.55 {accent}, stop:0.7 {entry_bg}, stop:1 {entry_bg});
}}
QTableView {{
    background: {surface}; alternate-background-color: {stripe};
    color: {text}; border: 1px solid {border}; gridline-color: transparent;
}}
QTableView::item:selected {{ background: {accent}; color: #ffffff; }}
QHeaderView::section {{
    background: {button_bg}; color: {text}; border: none;
    border-right: 1px solid {border}; padding: 6px 8px; font-weight: bold;
}}
QStatusBar {{ background: {surface}; color: {muted}; }}
QStatusBar QLabel {{ background: {surface}; color: {muted}; }}
QMenu {{ background: {surface}; color: {text}; border: 1px solid {border}; }}
QMenu::item:selected {{ background: {accent}; color: #ffffff; }}
QScrollBar:vertical {{ background: {surface}; width: 12px; }}
QScrollBar::handle:vertical {{ background: {button_bg}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {button_hover}; }}
QScrollBar:horizontal {{ background: {surface}; height: 12px; }}
QScrollBar::handle:horizontal {{ background: {button_bg}; border-radius: 5px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {button_hover}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
"""


def build_qss():
    # QSS 的 url() 需要正斜杠路径（Windows 上也是）
    check_svg = resource_path(os.path.join("assets", "check.svg")).replace("\\", "/")
    return QSS_TEMPLATE.format(
        bg=BG, surface=SURFACE, entry_bg=ENTRY_BG, stripe=STRIPE_BG,
        border=BORDER, accent=ACCENT, accent_hover=ACCENT_HOVER,
        accent_pressed=ACCENT_PRESSED, text=TEXT, muted=MUTED,
        button_bg=BUTTON_BG, button_hover=BUTTON_HOVER, check_svg=check_svg,
    )


class ResultsModel(QAbstractTableModel):
    """搜索结果模型。行数据存为元组列表，排序用 Python sorted 一次完成。
    QTableWidget 逐项存储 + Python __lt__ 逐对比较在十万行级别会卡死界面
    数秒（约 n·log n 次跨语言调用）；模型化后排序只需零点几秒。"""

    SORT_KEYS = (
        lambda r: r[0].lower(),   # 文件名（含 📁 前缀，与显示分组一致）
        lambda r: r[1].lower(),   # 路径
        lambda r: r[4],           # 大小（字节数，文件夹为 -1）
        lambda r: r[5],           # 修改日期（格式固定，字符串序即时间序）
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        # 行元组: (显示名, 父目录, 完整路径, 大小文本, 大小字节, 修改时间, 是否文件夹)
        self.rows = []
        self.headers = ["", "", "", ""]
        self._folder_brush = QBrush(QColor(FOLDER_FG))

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 4

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r = self.rows[index.row()]
        col = index.column()
        if role == Qt.DisplayRole:
            return (r[0], r[1], r[3], r[5])[col]
        if role == Qt.ForegroundRole and r[6]:
            return self._folder_brush
        if role == Qt.TextAlignmentRole and col == 2:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        if role == Qt.ToolTipRole:
            # 名字被省略显示时悬停可见全名；其余列显示完整路径
            return r[0] if col == 0 else r[2]
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def set_headers(self, headers):
        self.headers = list(headers)
        self.headerDataChanged.emit(Qt.Horizontal, 0, len(self.headers) - 1)

    def append_rows(self, rows):
        start = len(self.rows)
        self.beginInsertRows(QModelIndex(), start, start + len(rows) - 1)
        self.rows.extend(rows)
        self.endInsertRows()

    def clear(self):
        self.beginResetModel()
        self.rows = []
        self.endResetModel()

    def path_at(self, row):
        return self.rows[row][2]

    def sort(self, column, order=Qt.AscendingOrder):
        if not self.rows or not 0 <= column < 4:
            return
        self.layoutAboutToBeChanged.emit()
        self.rows.sort(key=self.SORT_KEYS[column],
                       reverse=(order == Qt.DescendingOrder))
        self.layoutChanged.emit()


class SearchSignals(QObject):
    """工作线程 → 界面线程的信号桥（Qt 信号跨线程自动排队）"""
    batch = Signal(int, list)
    progress = Signal(int, int)
    done = Signal(int, int, str)
    error = Signal(int, str)


class UpdateSignals(QObject):
    """更新检查/下载线程 → 界面线程"""
    status = Signal(str)                  # 状态栏文本（下载进度等）
    latest = Signal(bool)                 # 已是最新（manual）
    found = Signal(str, str, str, bool)   # tag, 下载地址, 文件名, manual
    ready = Signal(str, str)              # tag, 安装包本地路径
    fail = Signal(str, bool)              # 错误消息, manual


class FileSearchWindow(QMainWindow):
    CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".file_search_config.json")

    def __init__(self):
        super().__init__()
        self.language = 'zh'
        self.search_history = []
        self.folder_history = []
        self.font_size = 13
        self.compact = False
        self.whole_word = False
        self.entry_filter = 'all'
        self.is_searching = False
        self.search_generation = 0  # 递增代数：旧搜索线程的残留信号按代数丢弃
        self._load_config()

        self.signals = SearchSignals()
        self.signals.batch.connect(self._add_batch)
        self.signals.progress.connect(self._on_progress)
        self.signals.done.connect(self._on_done)
        self.signals.error.connect(self._on_error)

        self._update_info = None      # 发现的新版本 (tag, url, 文件名)
        self._update_busy = False
        self.update_signals = UpdateSignals()

        self._build_ui()

        self.update_signals.status.connect(self.status_label.setText)
        self.update_signals.latest.connect(self._on_update_latest)
        self.update_signals.found.connect(self._on_update_found)
        self.update_signals.ready.connect(self._on_update_ready)
        self.update_signals.fail.connect(self._on_update_fail)

        self.apply_language()
        self._apply_font_size()
        # 启动 3 秒后后台静默检查更新（有新版时“检查更新”按钮变为“升级到 vX.Y.Z”）
        QTimer.singleShot(3000, lambda: self._start_update_check(manual=False))

    # ---------- 配置 ----------

    def _load_config(self):
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
        lang = cfg.get('language', 'zh')
        self.language = lang if lang in TRANSLATIONS else 'zh'
        self.search_history = cfg.get('search_history', []) or []
        self.folder_history = cfg.get('folder_history', []) or []
        last = cfg.get('last_folder', os.getcwd())
        self.last_folder = last if os.path.isdir(last) else os.getcwd()
        fs = cfg.get('font_size', 13)
        self.font_size = int(fs) if isinstance(fs, (int, float)) and 8 <= fs <= 32 else 13
        self.compact = bool(cfg.get('compact_display', False))
        self.whole_word = bool(cfg.get('whole_word', False))
        ef = cfg.get('entry_filter', 'all')
        self.entry_filter = ef if ef in ('all', 'files', 'folders') else 'all'

    def _save_config(self):
        try:
            cfg = {
                'last_folder': self.folder_combo.currentText(),
                'search_history': self.search_history[:10],
                'folder_history': self.folder_history[:10],
                'compact_display': self.compact_check.isChecked(),
                'whole_word': self.whole_word_check.isChecked(),
                'entry_filter': self._entry_filter_value(),
                'font_size': self.font_size,
                'language': self.language,
            }
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件出错: {e}")

    def t(self, key, **kwargs):
        text = TRANSLATIONS.get(self.language, TRANSLATIONS['zh']).get(key)
        if text is None:
            text = TRANSLATIONS['zh'].get(key, key)
        return text.format(**kwargs) if kwargs else text

    # ---------- UI ----------

    def _build_ui(self):
        self.resize(920, 640)
        self.setMinimumSize(780, 520)
        icon_path = resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(14, 12, 14, 8)
        outer.setSpacing(8)

        # 顶部卡片：表单 + 选项
        card = QFrame(objectName="card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)
        outer.addWidget(card)

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        card_layout.addLayout(grid)

        self.folder_label = QLabel()
        grid.addWidget(self.folder_label, 0, 0, Qt.AlignRight)
        self.folder_combo = QComboBox(editable=True)
        self.folder_combo.setInsertPolicy(QComboBox.NoInsert)
        self.folder_combo.addItems(self.folder_history)
        self.folder_combo.setCurrentText(self.last_folder)
        self.folder_combo.lineEdit().returnPressed.connect(self.start_search_now)
        grid.addWidget(self.folder_combo, 0, 1)
        self.browse_button = QPushButton()
        self.browse_button.clicked.connect(self.browse_folder)
        grid.addWidget(self.browse_button, 0, 2)

        self.search_label = QLabel()
        grid.addWidget(self.search_label, 1, 0, Qt.AlignRight)
        self.search_combo = QComboBox(editable=True)
        self.search_combo.setInsertPolicy(QComboBox.NoInsert)
        self.search_combo.addItems(self.search_history)
        self.search_combo.setCurrentText("")
        self.search_combo.lineEdit().returnPressed.connect(self.start_search_now)
        grid.addWidget(self.search_combo, 1, 1)
        self.search_button = QPushButton(objectName="accent")
        self.search_button.clicked.connect(self.start_or_cancel_search)
        grid.addWidget(self.search_button, 1, 2)

        self.hint_label = QLabel(objectName="hint")
        grid.addWidget(self.hint_label, 2, 1, 1, 2)

        # 选项行
        opts = QHBoxLayout()
        opts.setSpacing(10)
        card_layout.addLayout(opts)
        self.name_radio = QRadioButton()
        self.name_radio.setChecked(True)
        self.content_radio = QRadioButton()
        self.all_radio = QRadioButton()
        self.all_radio.setChecked(True)
        self.any_radio = QRadioButton()
        # 两组单选需要各自独立（放同一布局中默认会互斥），用 QButtonGroup 分组
        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.name_radio)
        self.type_group.addButton(self.content_radio)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.all_radio)
        self.mode_group.addButton(self.any_radio)
        # 结果类型：全部 / 仅文件 / 仅文件夹
        self.entry_all_radio = QRadioButton()
        self.entry_files_radio = QRadioButton()
        self.entry_folders_radio = QRadioButton()
        {'files': self.entry_files_radio,
         'folders': self.entry_folders_radio}.get(
            self.entry_filter, self.entry_all_radio).setChecked(True)
        self.entry_group = QButtonGroup(self)
        for w in (self.entry_all_radio, self.entry_files_radio, self.entry_folders_radio):
            self.entry_group.addButton(w)
        self.whole_word_check = QCheckBox()
        self.whole_word_check.setChecked(self.whole_word)
        self.compact_check = QCheckBox()
        self.compact_check.setChecked(self.compact)
        self.compact_check.toggled.connect(self._apply_row_height)
        for w in (self.name_radio, self.content_radio):
            opts.addWidget(w)
        opts.addWidget(self._separator())
        for w in (self.all_radio, self.any_radio):
            opts.addWidget(w)
        opts.addWidget(self._separator())
        for w in (self.entry_all_radio, self.entry_files_radio, self.entry_folders_radio):
            opts.addWidget(w)
        opts.addWidget(self._separator())
        opts.addWidget(self.whole_word_check)
        opts.addWidget(self._separator())
        opts.addWidget(self.compact_check)
        opts.addStretch(1)

        # 结果区
        self.result_label = QLabel()
        outer.addWidget(self.result_label)

        self.results_model = ResultsModel(self)
        self.table = QTableView()
        self.table.setModel(self.results_model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        # 关闭自动折行：长文件名是不可折断的整词，折行会被挤出单行行高，
        # 只剩“…”；关闭后按字符截断，能显示的部分尽量显示，末尾才是“…”
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.setColumnWidth(0, 250)
        self.table.setColumnWidth(1, 320)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 170)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(lambda _: self.open_selected_file())
        outer.addWidget(self.table, 1)

        # 状态栏
        sb = self.statusBar()
        self.status_label = QLabel()
        sb.addWidget(self.status_label, 1)
        self.language_button = QPushButton(objectName="small")
        self.language_button.clicked.connect(self.toggle_language)
        sb.addPermanentWidget(self.language_button)
        self.font_label = QLabel()
        sb.addPermanentWidget(self.font_label)
        self.font_minus = QPushButton("−", objectName="small")
        self.font_minus.clicked.connect(lambda: self.change_font_size(-1))
        sb.addPermanentWidget(self.font_minus)
        self.font_plus = QPushButton("+", objectName="small")
        self.font_plus.clicked.connect(lambda: self.change_font_size(1))
        sb.addPermanentWidget(self.font_plus)

        # 右键菜单
        self.context_menu = QMenu(self)
        self.act_open = QAction(self)
        self.act_open.triggered.connect(self.open_selected_file)
        self.act_open_folder = QAction(self)
        self.act_open_folder.triggered.connect(self.open_containing_folder)
        self.act_copy_path = QAction(self)
        self.act_copy_path.triggered.connect(self.copy_file_path)
        self.act_copy_item = QAction(self)
        self.act_copy_item.triggered.connect(self.copy_file_or_folder)
        self.context_menu.addAction(self.act_open)
        self.context_menu.addAction(self.act_open_folder)
        self.context_menu.addSeparator()
        self.context_menu.addAction(self.act_copy_path)
        self.context_menu.addAction(self.act_copy_item)

        # 语言菜单：只在 macOS 挂菜单栏（原生显示在屏幕顶部），其他平台用状态栏按钮
        self.language_actions = {}
        if sys.platform == "darwin":
            self.language_menu = self.menuBar().addMenu("")
            group = QActionGroup(self)
            for lang, label in (("zh", "中文"), ("en", "English")):
                act = QAction(label, self, checkable=True)
                act.setChecked(lang == self.language)
                act.triggered.connect(lambda _, l=lang: self.set_language(l))
                group.addAction(act)
                self.language_menu.addAction(act)
                self.language_actions[lang] = act

        # 快捷键：Cmd/Ctrl +/- 调字体，Esc 取消搜索
        QShortcut(QKeySequence.ZoomIn, self, lambda: self.change_font_size(1))
        QShortcut(QKeySequence("Ctrl+="), self, lambda: self.change_font_size(1))
        QShortcut(QKeySequence.ZoomOut, self, lambda: self.change_font_size(-1))
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.cancel_search)

        # 系统托盘：关闭主窗口后驻留后台（macOS 显示在菜单栏右上角）
        self.tray_menu = QMenu(self)
        self.act_tray_show = QAction(self)
        self.act_tray_show.triggered.connect(self._show_main_window)
        self.act_tray_update = QAction(self)
        self.act_tray_update.triggered.connect(self.check_or_apply_update)
        self.act_tray_quit = QAction(self)
        self.act_tray_quit.triggered.connect(QApplication.quit)
        self.tray_menu.addAction(self.act_tray_show)
        self.tray_menu.addAction(self.act_tray_update)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.act_tray_quit)
        self.tray = QSystemTrayIcon(
            QIcon(resource_path(os.path.join("assets", "icon.png"))), self)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _show_main_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._show_main_window()

    def eventFilter(self, obj, event):
        # macOS 点 Dock 图标重新激活时，若主窗口已隐藏则重新显示
        if event.type() == QEvent.ApplicationActivate and not self.isVisible():
            self._show_main_window()
        return super().eventFilter(obj, event)

    def _separator(self):
        sep = QLabel("|")
        sep.setStyleSheet(f"color: {BORDER};")
        return sep

    # ---------- 语言 ----------

    def set_language(self, lang):
        if lang not in TRANSLATIONS or lang == self.language:
            return
        self.language = lang
        self.apply_language()
        self._save_config()

    def toggle_language(self):
        self.set_language('en' if self.language == 'zh' else 'zh')

    def apply_language(self):
        t = self.t
        self.setWindowTitle(f"{t('app_title')} v{APP_VERSION}")
        self.tray.setToolTip(t('app_title'))
        self.act_tray_show.setText(t('tray_show'))
        self.act_tray_quit.setText(t('tray_quit'))
        if self._update_info:
            self.act_tray_update.setText(t('update_button_new', tag=self._update_info[0]))
        else:
            self.act_tray_update.setText(t('check_update'))
        self.folder_label.setText(t('search_folder'))
        self.browse_button.setText(t('browse'))
        self.search_label.setText(t('search_keywords'))
        self.search_button.setText(t('cancel') if self.is_searching else t('search'))
        self.hint_label.setText(t('hint'))
        self.name_radio.setText(t('by_name'))
        self.content_radio.setText(t('by_content'))
        self.all_radio.setText(t('match_all'))
        self.any_radio.setText(t('match_any'))
        self.entry_all_radio.setText(t('entry_all'))
        self.entry_files_radio.setText(t('entry_files'))
        self.entry_folders_radio.setText(t('entry_folders'))
        self.whole_word_check.setText(t('whole_word'))
        self.whole_word_check.setToolTip(t('whole_word_tip'))
        self.compact_check.setText(t('compact'))
        self.result_label.setText(t('results'))
        self.font_label.setText(t('font'))
        self.results_model.set_headers(
            [t('col_name'), t('col_path'), t('col_size'), t('col_date')])
        self.act_open.setText(t('open_file'))
        self.act_open_folder.setText(t('open_containing'))
        self.act_copy_path.setText(t('copy_path'))
        self.act_copy_item.setText(t('copy_item'))
        self.language_button.setText("EN" if self.language == 'zh' else "中文")
        if sys.platform == "darwin":
            self.language_menu.setTitle(t('menu_language'))
            for lang, act in self.language_actions.items():
                act.setChecked(lang == self.language)
        if not self.is_searching:
            self.status_label.setText(t('ready'))

    # ---------- 字体 / 行高 ----------

    def change_font_size(self, delta):
        new_size = max(8, min(32, self.font_size + delta))
        if new_size == self.font_size:
            return
        self.font_size = new_size
        self._apply_font_size()
        self.status_label.setText(self.t('font_size_status', size=new_size))
        self._save_config()

    def _apply_font_size(self):
        font = QApplication.font()
        font.setPointSize(self.font_size)
        QApplication.setFont(font)
        # 已创建的控件需要显式刷新字体
        for w in self.findChildren(QWidget):
            w.setFont(font)
        hint_font = QFont(font)
        hint_font.setPointSize(max(9, self.font_size - 2))
        self.hint_label.setFont(hint_font)
        self.font_label.setFont(hint_font)
        self._apply_row_height()

    def _apply_row_height(self):
        if self.compact_check.isChecked():
            height = max(20, int(self.font_size * 1.4))
        else:
            height = max(30, int(self.font_size * 2.3))
        self.table.verticalHeader().setDefaultSectionSize(height)
        self._save_config()

    # ---------- 历史记录 ----------

    def _remember(self, history, value):
        value = value.strip()
        if not value:
            return history
        if value in history:
            history.remove(value)
        history.insert(0, value)
        return history[:10]

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t('search_folder'),
                                                  self.folder_combo.currentText() or os.getcwd())
        if folder:
            self.folder_combo.setCurrentText(folder)
            self.folder_history = self._remember(self.folder_history, folder)
            self._refresh_combo(self.folder_combo, self.folder_history, folder)
            self._save_config()

    def _refresh_combo(self, combo, items, current):
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)
        combo.setCurrentText(current)
        combo.blockSignals(False)

    # ---------- 搜索（逻辑移植自 Tk 版） ----------

    @staticmethod
    def parse_search_terms(search_text):
        return [term.strip() for term in search_text.split() if term.strip()]

    @staticmethod
    def word_pattern(kw_lower):
        """全词匹配的正则：关键词的字母/数字端不得与相邻字母/数字连成一体。
        仅约束 ASCII 字母数字端（中文等 CJK 词天然无分隔符，不加约束），
        因此 a3 匹配 zhiyuan_a3_video / 智元a3，但不匹配 e183a375。"""
        pre = r'(?<![a-z0-9])' if re.match(r'[a-z0-9]', kw_lower) else ''
        post = r'(?![a-z0-9])' if re.search(r'[a-z0-9]$', kw_lower) else ''
        return pre + re.escape(kw_lower) + post

    @classmethod
    def keyword_in(cls, kw, text_lower, whole_word, at_text_end_ok=True):
        """text_lower 中是否命中 kw。at_text_end_ok=False 时不信任恰好贴着文本
        末尾结束的命中（分块读取时看不到下一个字符，无法判定词边界）。"""
        if not whole_word:
            return kw in text_lower
        for m in re.finditer(cls.word_pattern(kw), text_lower):
            if at_text_end_ok or m.end() < len(text_lower):
                return True
        return False

    @classmethod
    def match_keywords(cls, text, keywords_lower, match_mode, whole_word=False):
        text_lower = text.lower()
        if match_mode == "all":
            return all(cls.keyword_in(kw, text_lower, whole_word) for kw in keywords_lower)
        return any(cls.keyword_in(kw, text_lower, whole_word) for kw in keywords_lower)

    @classmethod
    def content_matches(cls, path, keywords_lower, match_mode, file_size=None,
                        chunk_size=4 * 1024 * 1024, whole_word=False):
        if file_size is not None and file_size <= chunk_size:
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return cls.match_keywords(f.read(), keywords_lower, match_mode, whole_word)
            except Exception:
                return False
        found = [False] * len(keywords_lower)
        # 全词模式 tail 多留一个字符，保证跨块命中重扫时能看到前一个字符判定词边界
        overlap = max(len(kw) for kw in keywords_lower) + (1 if whole_word else -1)
        tail = ""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                chunk = f.read(chunk_size)
                while chunk:
                    next_chunk = f.read(chunk_size)
                    at_eof = not next_chunk
                    text = (tail + chunk).lower()
                    for i, kw in enumerate(keywords_lower):
                        if not found[i] and cls.keyword_in(kw, text, whole_word, at_eof):
                            if match_mode != "all":
                                return True
                            found[i] = True
                    if match_mode == "all" and all(found):
                        return True
                    tail = text[-overlap:] if overlap > 0 else ""
                    chunk = next_chunk
        except Exception:
            return False
        return match_mode == "all" and all(found)

    def start_search_now(self):
        """输入框回车：始终按当前关键词立即搜索。上一次搜索还在进行时先自动取消，
        避免「第一次回车只是取消、要按第二次才搜索」"""
        if self.is_searching:
            self.cancel_search()
        self.start_or_cancel_search()

    def start_or_cancel_search(self):
        # 「搜索/取消」按钮保持切换语义：搜索中点击即取消
        if self.is_searching:
            self.cancel_search()
            return
        search_path = self.folder_combo.currentText().strip()
        search_text = self.search_combo.currentText()
        if not os.path.isdir(search_path):
            QMessageBox.critical(self, self.t('error'),
                                 self.t('invalid_folder', path=search_path))
            return
        keywords = self.parse_search_terms(search_text)
        if not keywords:
            QMessageBox.warning(self, self.t('warning'), self.t('enter_keywords'))
            return

        self.search_history = self._remember(self.search_history, search_text)
        self._refresh_combo(self.search_combo, self.search_history, search_text)
        self.folder_history = self._remember(self.folder_history, search_path)
        self._refresh_combo(self.folder_combo, self.folder_history, search_path)
        self._save_config()

        self.table.setSortingEnabled(False)
        self.results_model.clear()
        self.is_searching = True
        self.search_generation += 1
        self.search_button.setText(self.t('cancel'))
        self.status_label.setText(self.t('searching', keywords=', '.join(keywords)))

        search_type = "name" if self.name_radio.isChecked() else "content"
        match_mode = "all" if self.all_radio.isChecked() else "any"
        whole_word = self.whole_word_check.isChecked()
        thread = threading.Thread(
            target=self._search_worker,
            args=(self.search_generation, search_path,
                  [kw.lower() for kw in keywords], search_type, match_mode,
                  whole_word, self._entry_filter_value()),
            daemon=True)
        thread.start()

    def _entry_filter_value(self):
        if self.entry_files_radio.isChecked():
            return 'files'
        if self.entry_folders_radio.isChecked():
            return 'folders'
        return 'all'

    def cancel_search(self):
        if self.is_searching:
            self.is_searching = False
            # 作废本次搜索：已排队但尚未送达的结果批次不得在恢复排序后再插入表格
            self.search_generation += 1
            self.search_button.setText(self.t('search'))
            self.status_label.setText(self.t('search_cancelled'))
            self.table.setSortingEnabled(True)

    def _search_worker(self, generation, search_path, keywords_lower,
                       search_type, match_mode, whole_word, entry_filter):
        def active():
            return self.is_searching and self.search_generation == generation

        try:
            count = 0
            batch = []
            batch_size = 50
            last_update = time.time()
            update_interval = 0.1

            def make_row(entry, st, is_folder):
                mtime = datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                parent = os.path.dirname(entry.path)
                if is_folder:
                    return (f"📁 {entry.name}", parent, entry.path,
                            self.t('folder_size'), -1, mtime, True)
                size = st.st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.2f} KB"
                else:
                    size_str = f"{size/(1024*1024):.2f} MB"
                return (entry.name, parent, entry.path, size_str, size, mtime, False)

            def flush():
                nonlocal batch
                if batch:
                    rows, batch = batch, []
                    self.signals.batch.emit(generation, rows)

            def scan(path):
                nonlocal count, last_update
                if not active():
                    return
                try:
                    with os.scandir(path) as entries:
                        dirs = []
                        for entry in entries:
                            if not active():
                                return
                            try:
                                if entry.is_dir(follow_symlinks=False):
                                    if (entry_filter != 'files'
                                            and search_type == "name"
                                            and self.match_keywords(
                                                entry.name, keywords_lower, match_mode, whole_word)):
                                        batch.append(make_row(
                                            entry, entry.stat(follow_symlinks=False), True))
                                        count += 1
                                    dirs.append(entry.path)
                                elif entry_filter != 'folders' and entry.is_file(follow_symlinks=False):
                                    if search_type == "name":
                                        if self.match_keywords(entry.name, keywords_lower,
                                                               match_mode, whole_word):
                                            batch.append(make_row(
                                                entry, entry.stat(follow_symlinks=False), False))
                                            count += 1
                                    else:
                                        st = entry.stat(follow_symlinks=False)
                                        if st.st_size <= 100 * 1024 * 1024 and self.content_matches(
                                                entry.path, keywords_lower, match_mode, st.st_size,
                                                whole_word=whole_word):
                                            batch.append(make_row(entry, st, False))
                                            count += 1
                                now = time.time()
                                if len(batch) >= batch_size or (now - last_update) > update_interval:
                                    flush()
                                    last_update = now
                                    self.signals.progress.emit(generation, count)
                            except (PermissionError, OSError):
                                continue
                        for d in dirs:
                            if not active():
                                return
                            scan(d)
                except (PermissionError, OSError):
                    pass

            scan(search_path)
            flush()
            if active():
                self.signals.done.emit(generation, count, match_mode)
        except Exception as e:
            self.signals.error.emit(generation, str(e))
        finally:
            if self.search_generation == generation:
                self.is_searching = False

    # ---------- 搜索结果（界面线程） ----------

    def _add_batch(self, generation, rows):
        if generation != self.search_generation:
            return  # 已取消/已重启的旧搜索残留结果
        self.results_model.append_rows(rows)

    def _on_progress(self, generation, count):
        if generation != self.search_generation:
            return
        self.status_label.setText(self.t('searching_progress', count=count))

    def _on_done(self, generation, count, match_mode):
        if generation != self.search_generation:
            return
        mode_text = self.t('mode_all') if match_mode == "all" else self.t('mode_any')
        self.status_label.setText(self.t('search_done', count=count, mode=mode_text))
        self.search_button.setText(self.t('search'))
        self.table.setSortingEnabled(True)

    def _on_error(self, generation, message):
        if generation != self.search_generation:
            return
        self.status_label.setText(self.t('search_error_status', error=message))
        QMessageBox.critical(self, self.t('error'),
                             self.t('search_error_msg', error=message))
        self.search_button.setText(self.t('search'))
        self.table.setSortingEnabled(True)

    # ---------- 一键升级 ----------

    def check_or_apply_update(self):
        """托盘菜单：未发现新版本时检查；已发现时直接开始下载安装"""
        if self._update_busy:
            return
        self._show_main_window()  # 进度和确认框都在主窗口上，先带出来
        if self._update_info:
            self._start_update_download()
        else:
            self._start_update_check(manual=True)

    def _start_update_check(self, manual):
        if self._update_busy or self._update_info:
            return
        self._update_busy = True
        if manual:
            self.status_label.setText(self.t('update_checking'))
        threading.Thread(target=self._update_check_worker, args=(manual,),
                         daemon=True).start()

    def _update_check_worker(self, manual):
        try:
            req = urllib.request.Request(RELEASES_API, headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "StellarSearchEverything"})
            with urllib.request.urlopen(req, timeout=15,
                                        context=https_context()) as resp:
                info = json.load(resp)
            tag = info.get("tag_name", "")
            if version_tuple(tag) <= version_tuple(APP_VERSION):
                self.update_signals.latest.emit(manual)
                return
            suffix = platform_asset_suffix()
            asset = next((a for a in info.get("assets", [])
                          if a.get("name", "").endswith(suffix)), None)
            if asset is None:
                self.update_signals.fail.emit(
                    self.t('update_no_asset', tag=tag), manual)
                return
            self.update_signals.found.emit(
                tag, asset["browser_download_url"], asset["name"], manual)
        except Exception as e:
            self.update_signals.fail.emit(str(e), manual)

    def _on_update_latest(self, manual):
        self._update_busy = False
        if manual:
            self.status_label.setText(self.t('update_latest', version=APP_VERSION))
            QMessageBox.information(self, self.t('check_update'),
                                    self.t('update_latest', version=APP_VERSION))

    def _on_update_found(self, tag, url, name, manual):
        self._update_busy = False
        self._update_info = (tag, url, name)
        self.act_tray_update.setText(self.t('update_button_new', tag=tag))
        self.status_label.setText(self.t('update_available', tag=tag))
        if manual:
            self._start_update_download()
        else:
            self.tray.showMessage(self.t('update_found_title'),
                                  self.t('update_available', tag=tag))

    def _on_update_fail(self, message, manual):
        self._update_busy = False
        self.act_tray_update.setEnabled(True)
        if manual:
            self.status_label.setText(self.t('update_error', error=message))
            QMessageBox.warning(self, self.t('check_update'),
                                self.t('update_error', error=message))

    def _start_update_download(self):
        tag, url, name = self._update_info
        if not getattr(sys, 'frozen', False):
            QMessageBox.information(self, self.t('update_found_title'),
                                    self.t('update_source_run', tag=tag))
            return
        ret = QMessageBox.question(
            self, self.t('update_found_title'),
            self.t('update_confirm', tag=tag, version=APP_VERSION))
        if ret != QMessageBox.Yes:
            return
        self._update_busy = True
        self.act_tray_update.setEnabled(False)
        threading.Thread(target=self._update_download_worker,
                         args=(tag, url, name), daemon=True).start()

    def _update_download_worker(self, tag, url, name):
        try:
            dest = os.path.join(tempfile.gettempdir(), name)
            req = urllib.request.Request(
                url, headers={"User-Agent": "StellarSearchEverything"})
            with urllib.request.urlopen(req, timeout=60,
                                        context=https_context()) as resp, \
                    open(dest, "wb") as out:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                while True:
                    block = resp.read(256 * 1024)
                    if not block:
                        break
                    out.write(block)
                    done += len(block)
                    if total:
                        self.update_signals.status.emit(self.t(
                            'update_downloading', percent=done * 100 // total))
            self.update_signals.ready.emit(tag, dest)
        except Exception as e:
            self.update_signals.fail.emit(str(e), True)

    def _on_update_ready(self, tag, installer):
        self.status_label.setText(self.t('update_installing'))
        try:
            if sys.platform == "darwin":
                self._install_update_macos(installer)
            elif sys.platform.startswith("win"):
                self._install_update_windows(installer)
            else:
                self._install_update_linux(installer)
        except Exception as e:
            self._on_update_fail(str(e), True)

    def _install_update_macos(self, dmg_path):
        """退出后挂载 DMG 原地替换 .app（去掉隔离属性，避免“无法验证开发者”）并重启"""
        exe = sys.executable
        pos = exe.find(".app/")
        if pos < 0:
            raise RuntimeError("未找到 .app 包路径")
        app_dir = exe[:pos + 4]
        mnt = os.path.join(tempfile.gettempdir(), "sse_update_mnt")
        script = os.path.join(tempfile.gettempdir(), "sse_update.sh")
        with open(script, "w") as f:
            f.write(f'''#!/bin/bash
while kill -0 {os.getpid()} 2>/dev/null; do sleep 0.3; done
hdiutil attach "{dmg_path}" -nobrowse -readonly -mountpoint "{mnt}" || exit 1
SRC=$(ls -d "{mnt}"/*.app | head -1)
rm -rf "{app_dir}"
ditto "$SRC" "{app_dir}"
hdiutil detach "{mnt}" -force
xattr -dr com.apple.quarantine "{app_dir}" 2>/dev/null
open "{app_dir}"
rm -f "{dmg_path}" "$0"
''')
        os.chmod(script, 0o755)
        subprocess.Popen(["/bin/bash", script], start_new_session=True)
        QApplication.quit()

    def _install_update_windows(self, setup_path):
        """退出后静默运行 Inno Setup 安装向导并重启"""
        ps = (f"Wait-Process -Id {os.getpid()} -ErrorAction SilentlyContinue; "
              f"Start-Process -FilePath '{setup_path}' "
              f"-ArgumentList '/VERYSILENT','/NORESTART' -Wait; "
              f"Start-Process -FilePath '{sys.executable}'")
        DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden",
                          "-Command", ps], creationflags=DETACHED)
        QApplication.quit()

    def _install_update_linux(self, deb_path):
        """退出后经 pkexec 安装 deb（弹系统授权框）并重启"""
        script = os.path.join(tempfile.gettempdir(), "sse_update.sh")
        with open(script, "w") as f:
            f.write(f'''#!/bin/sh
while kill -0 {os.getpid()} 2>/dev/null; do sleep 0.3; done
pkexec dpkg -i "{deb_path}" || exit 1
rm -f "{deb_path}" "$0"
"{sys.executable}" &
''')
        os.chmod(script, 0o755)
        subprocess.Popen(["/bin/sh", script], start_new_session=True)
        QApplication.quit()

    # ---------- 结果操作 ----------

    def _selected_paths(self):
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        return [self.results_model.path_at(row) for row in rows]

    def _show_context_menu(self, pos):
        if self.table.indexAt(pos).isValid():
            self.context_menu.exec(self.table.viewport().mapToGlobal(pos))

    def open_selected_file(self):
        for path in self._selected_paths()[:10]:
            self._open_path(path)

    def _open_path(self, path):
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            elif sys.platform == "win32":
                os.startfile(path)  # noqa
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as e:
            QMessageBox.critical(self, self.t('error'),
                                 self.t('cannot_open_file', error=str(e)))

    def open_containing_folder(self):
        paths = self._selected_paths()
        if not paths:
            return
        path = paths[0]
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", "-R", path], check=False)
            elif sys.platform == "win32":
                subprocess.run(["explorer", "/select,", os.path.normpath(path)], check=False)
            else:
                self._open_path(os.path.dirname(path))
        except Exception as e:
            QMessageBox.critical(self, self.t('error'),
                                 self.t('cannot_open_folder', error=str(e)))

    def copy_file_path(self):
        paths = self._selected_paths()
        if not paths:
            return
        QApplication.clipboard().setText("\n".join(paths))
        if len(paths) == 1:
            self.status_label.setText(self.t('copied_path', path=paths[0]))
        else:
            self.status_label.setText(self.t('copied_paths', count=len(paths)))

    def copy_file_or_folder(self):
        """复制文件/文件夹到剪贴板（可直接在文件管理器里粘贴）。

        Qt 的 QMimeData URL 剪贴板在 macOS/Windows/Linux 上原生支持，
        替代了 Tk 版的 pyobjc/AppleScript 方案。
        """
        paths = [p for p in self._selected_paths() if os.path.exists(p)]
        if not paths:
            QMessageBox.warning(self, self.t('warning'), self.t('no_valid_paths'))
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(os.path.abspath(p)) for p in paths])
        QApplication.clipboard().setMimeData(mime)
        files = sum(1 for p in paths if os.path.isfile(p))
        folders = len(paths) - files
        if len(paths) == 1:
            key = 'copied_file' if files else 'copied_folder'
            self.status_label.setText(self.t(key, name=os.path.basename(paths[0])))
        elif files and folders:
            self.status_label.setText(self.t('copied_mixed', files=files, folders=folders))
        elif files:
            self.status_label.setText(self.t('copied_files', files=files))
        else:
            self.status_label.setText(self.t('copied_folders', folders=folders))

    # ---------- 关闭 ----------

    def closeEvent(self, event):
        self._save_config()
        if self.tray.isVisible():
            # 关闭窗口 → 隐藏到托盘驻留后台；托盘菜单“退出”才真正退出
            event.ignore()
            self.hide()
            return
        self.is_searching = False
        event.accept()


def main():
    setup_launch_log()
    # Linux Wayland 会话下优先用原生 wayland 平台插件：
    # X11/XWayland 的交互式缩放是异步的（边框先动、内容后画），
    # 拖拽时会抖动/闪烁；wayland 下逐帧同步，无此问题。
    # 分号列表表示 wayland 不可用时自动回退 xcb；用户可用 QT_QPA_PLATFORM 覆盖。
    if sys.platform.startswith("linux") and "QT_QPA_PLATFORM" not in os.environ:
        if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland":
            os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

    app = QApplication(sys.argv)
    # 应用级图标：macOS Dock / 任务栏用的是这个，窗口级 setWindowIcon 管不到
    icon_path = resource_path(os.path.join("assets", "icon.png"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    app.setStyle("Fusion")  # 跨平台一致的基础样式，暗色 QSS 在其上生效
    app.setStyleSheet(build_qss())
    app.setQuitOnLastWindowClosed(False)  # 关窗后驻留托盘，退出走托盘菜单
    window = FileSearchWindow()
    app.installEventFilter(window)        # Dock 图标激活时恢复主窗口
    app.aboutToQuit.connect(window._save_config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
