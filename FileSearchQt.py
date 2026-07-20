"""Stellar Search Everything — PySide6 版本。

从 Tkinter 版（FileSearchGUI.py）迁移：搜索逻辑原样移植，UI 用 Qt 重写。
配置文件（~/.file_search_config.json）与 Tk 版完全兼容。
"""
import os
import sys
import json
import time
import datetime
import subprocess
import threading

from PySide6.QtCore import Qt, QObject, Signal, QUrl, QMimeData
from PySide6.QtGui import (QIcon, QAction, QActionGroup, QFont, QKeySequence,
                           QShortcut, QColor, QBrush)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QComboBox, QPushButton,
    QRadioButton, QCheckBox, QHBoxLayout, QVBoxLayout, QGridLayout,
    QTableWidget, QTableWidgetItem, QMenu, QFileDialog, QMessageBox,
    QHeaderView, QFrame, QAbstractItemView, QButtonGroup,
)

from translations import TRANSLATIONS


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
QTableWidget {{
    background: {surface}; alternate-background-color: {stripe};
    color: {text}; border: 1px solid {border}; gridline-color: transparent;
}}
QTableWidget::item:selected {{ background: {accent}; color: #ffffff; }}
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


class SortableItem(QTableWidgetItem):
    """按 UserRole 中的排序键比较（文件名不区分大小写、大小按字节数）"""

    def __lt__(self, other):
        a = self.data(Qt.UserRole)
        b = other.data(Qt.UserRole)
        if a is not None and b is not None:
            return a < b
        return super().__lt__(other)


class SearchSignals(QObject):
    """工作线程 → 界面线程的信号桥（Qt 信号跨线程自动排队）"""
    batch = Signal(int, list)
    progress = Signal(int, int)
    done = Signal(int, int, str)
    error = Signal(int, str)


class FileSearchWindow(QMainWindow):
    CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".file_search_config.json")

    def __init__(self):
        super().__init__()
        self.language = 'zh'
        self.search_history = []
        self.folder_history = []
        self.font_size = 13
        self.compact = False
        self.is_searching = False
        self.search_generation = 0  # 递增代数：旧搜索线程的残留信号按代数丢弃
        self._load_config()

        self.signals = SearchSignals()
        self.signals.batch.connect(self._add_batch)
        self.signals.progress.connect(self._on_progress)
        self.signals.done.connect(self._on_done)
        self.signals.error.connect(self._on_error)

        self._build_ui()
        self.apply_language()
        self._apply_font_size()

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

    def _save_config(self):
        try:
            cfg = {
                'last_folder': self.folder_combo.currentText(),
                'search_history': self.search_history[:10],
                'folder_history': self.folder_history[:10],
                'compact_display': self.compact_check.isChecked(),
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
        self.folder_combo.lineEdit().returnPressed.connect(self.start_or_cancel_search)
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
        self.search_combo.lineEdit().returnPressed.connect(self.start_or_cancel_search)
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
        self.compact_check = QCheckBox()
        self.compact_check.setChecked(self.compact)
        self.compact_check.toggled.connect(self._apply_row_height)
        for w in (self.name_radio, self.content_radio):
            opts.addWidget(w)
        opts.addWidget(self._separator())
        for w in (self.all_radio, self.any_radio):
            opts.addWidget(w)
        opts.addWidget(self._separator())
        opts.addWidget(self.compact_check)
        opts.addStretch(1)

        # 结果区
        self.result_label = QLabel()
        outer.addWidget(self.result_label)

        self.table = QTableWidget(0, 4)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
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
        self.setWindowTitle(t('app_title'))
        self.folder_label.setText(t('search_folder'))
        self.browse_button.setText(t('browse'))
        self.search_label.setText(t('search_keywords'))
        self.search_button.setText(t('cancel') if self.is_searching else t('search'))
        self.hint_label.setText(t('hint'))
        self.name_radio.setText(t('by_name'))
        self.content_radio.setText(t('by_content'))
        self.all_radio.setText(t('match_all'))
        self.any_radio.setText(t('match_any'))
        self.compact_check.setText(t('compact'))
        self.result_label.setText(t('results'))
        self.font_label.setText(t('font'))
        self.table.setHorizontalHeaderLabels(
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
    def match_keywords(text, keywords_lower, match_mode):
        text_lower = text.lower()
        if match_mode == "all":
            return all(kw in text_lower for kw in keywords_lower)
        return any(kw in text_lower for kw in keywords_lower)

    @classmethod
    def content_matches(cls, path, keywords_lower, match_mode, file_size=None,
                        chunk_size=4 * 1024 * 1024):
        if file_size is not None and file_size <= chunk_size:
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return cls.match_keywords(f.read(), keywords_lower, match_mode)
            except Exception:
                return False
        found = [False] * len(keywords_lower)
        overlap = max(len(kw) for kw in keywords_lower) - 1
        tail = ""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    text = (tail + chunk).lower()
                    for i, kw in enumerate(keywords_lower):
                        if not found[i] and kw in text:
                            if match_mode != "all":
                                return True
                            found[i] = True
                    if match_mode == "all" and all(found):
                        return True
                    tail = text[-overlap:] if overlap > 0 else ""
        except Exception:
            return False
        return match_mode == "all" and all(found)

    def start_or_cancel_search(self):
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
        self.table.setRowCount(0)
        self.is_searching = True
        self.search_generation += 1
        self.search_button.setText(self.t('cancel'))
        self.status_label.setText(self.t('searching', keywords=', '.join(keywords)))

        search_type = "name" if self.name_radio.isChecked() else "content"
        match_mode = "all" if self.all_radio.isChecked() else "any"
        thread = threading.Thread(
            target=self._search_worker,
            args=(self.search_generation, search_path,
                  [kw.lower() for kw in keywords], search_type, match_mode),
            daemon=True)
        thread.start()

    def cancel_search(self):
        if self.is_searching:
            self.is_searching = False
            # 作废本次搜索：已排队但尚未送达的结果批次不得在恢复排序后再插入表格
            self.search_generation += 1
            self.search_button.setText(self.t('search'))
            self.status_label.setText(self.t('search_cancelled'))
            self.table.setSortingEnabled(True)

    def _search_worker(self, generation, search_path, keywords_lower, search_type, match_mode):
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
                                    if search_type == "name" and self.match_keywords(
                                            entry.name, keywords_lower, match_mode):
                                        batch.append(make_row(
                                            entry, entry.stat(follow_symlinks=False), True))
                                        count += 1
                                    dirs.append(entry.path)
                                elif entry.is_file(follow_symlinks=False):
                                    if search_type == "name":
                                        if self.match_keywords(entry.name, keywords_lower, match_mode):
                                            batch.append(make_row(
                                                entry, entry.stat(follow_symlinks=False), False))
                                            count += 1
                                    else:
                                        st = entry.stat(follow_symlinks=False)
                                        if st.st_size <= 100 * 1024 * 1024 and self.content_matches(
                                                entry.path, keywords_lower, match_mode, st.st_size):
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
        table = self.table
        start = table.rowCount()
        table.setRowCount(start + len(rows))
        for i, (name, parent, path, size_str, size_bytes, mtime, is_folder) in enumerate(rows):
            row = start + i
            name_item = SortableItem(name)
            name_item.setData(Qt.UserRole, name.lower())
            name_item.setData(Qt.UserRole + 1, path)  # 完整路径存在数据里，不再需要隐藏列
            name_item.setToolTip(name)  # 名字被省略显示（“…”）时悬停可见全名
            path_item = SortableItem(parent)
            path_item.setData(Qt.UserRole, parent.lower())
            path_item.setToolTip(path)
            size_item = SortableItem(size_str)
            size_item.setData(Qt.UserRole, size_bytes)
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            mtime_item = SortableItem(mtime)
            mtime_item.setData(Qt.UserRole, mtime)
            items = (name_item, path_item, size_item, mtime_item)
            folder_brush = QBrush(QColor(FOLDER_FG)) if is_folder else None
            for col, item in enumerate(items):
                if folder_brush:
                    item.setForeground(folder_brush)
                table.setItem(row, col, item)

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

    # ---------- 结果操作 ----------

    def _selected_paths(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        paths = []
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                paths.append(item.data(Qt.UserRole + 1))
        return paths

    def _show_context_menu(self, pos):
        if self.table.itemAt(pos):
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
        self.is_searching = False
        self._save_config()
        event.accept()


def main():
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
    window = FileSearchWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
