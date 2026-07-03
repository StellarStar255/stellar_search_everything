import os
import sys
import glob
import re
import time
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import subprocess
import datetime
import json
import threading
import plistlib
from urllib.parse import quote
from PIL import Image, ImageTk, ImageDraw  # Add this import


def resource_path(relative_path):
    """获取资源文件的绝对路径（兼容打包后的应用）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # 开发时使用脚本所在目录
        return os.path.join(os.path.dirname(__file__), relative_path)


# 界面文案（中/英），通过菜单栏"语言/Language"切换
TRANSLATIONS = {
    'zh': {
        'app_title': "文件搜索工具",
        'menu_language': "语言",
        'search_folder': "搜索文件夹",
        'browse': "浏览…",
        'search_keywords': "搜索关键词",
        'search': "搜索",
        'cancel': "取消",
        'hint': "支持多关键词，用空格分隔；双击输入框可选择历史记录",
        'by_name': "按文件名",
        'by_content': "按内容",
        'match_all': "包含所有关键词",
        'match_any': "包含任一关键词",
        'compact': "紧凑显示",
        'results': "搜索结果",
        'open_file': "打开文件",
        'open_containing': "打开所在文件夹",
        'copy_path': "复制路径",
        'copy_item': "复制文件/文件夹",
        'ready': "就绪",
        'font': "字体",
        'col_name': "文件名",
        'col_path': "路径",
        'col_size': "大小",
        'col_date': "修改日期",
        'font_size_status': "字体大小: {size}",
        'error': "错误",
        'warning': "警告",
        'notice': "提示",
        'invalid_folder': "无效的文件夹路径: {path}",
        'enter_keywords': "请输入搜索关键词",
        'enter_valid_keywords': "请输入有效的搜索关键词",
        'searching': "正在搜索关键词: {keywords}...",
        'searching_progress': "正在搜索... 已找到 {count} 个结果",
        'mode_all': "所有关键词",
        'mode_any': "任一关键词",
        'search_done': "搜索完成，找到 {count} 个包含{mode}的结果",
        'search_error_status': "搜索出错: {error}",
        'search_error_msg': "搜索过程中发生错误: {error}",
        'search_cancelled': "搜索已取消",
        'cannot_open_file': "无法打开文件: {error}",
        'cannot_open_folder': "无法打开文件夹: {error}",
        'copied_path': "已复制路径: {path}",
        'copied_paths': "已复制 {count} 条路径",
        'cannot_copy_path': "无法复制路径: {error}",
        'no_valid_paths': "没有有效的文件路径",
        'copied_file': "✅ 已复制文件: {name}",
        'copied_folder': "✅ 已复制文件夹: {name}",
        'copied_mixed': "✅ 已复制 {files} 个文件和 {folders} 个文件夹",
        'copied_files': "✅ 已复制 {files} 个文件",
        'copied_folders': "✅ 已复制 {folders} 个文件夹",
        'copied_path_text': "已复制路径（文本格式）",
        'copy_failed_status': "❌ 复制失败: {error}",
        'copy_failed': "❌ 复制失败",
        'copy_error': "复制操作发生错误: {error}",
        'pyobjc_ask': "无法将文件复制到剪贴板（可能需要安装 pyobjc）。\n"
                      "已复制文件路径为文本。\n\n"
                      "是否要查看安装 pyobjc 的说明？",
        'pyobjc_howto_title': "安装说明",
        'pyobjc_howto': "在终端中运行以下命令安装 pyobjc：\n\n"
                        "pip install pyobjc-framework-Cocoa\n\n"
                        "或使用 pip3:\n"
                        "pip3 install pyobjc-framework-Cocoa\n\n"
                        "安装后重启程序即可获得完整的剪贴板功能。",
        'sort_error': "排序时发生错误: {error}",
        'cjk_font_missing': "未检测到中文字体，界面中的中文会显示为方块。\n\n"
                            "请在终端运行以下命令安装中文字体：\n"
                            "sudo apt install fonts-noto-cjk\n\n"
                            "安装完成后重新启动本程序。\n\n"
                            "诊断信息：当前字体 {font}，Tk 可见字体 {count} 个。\n"
                            "若系统已装中文字体但这里数量很少，"
                            "说明当前 Python 的 Tk 不支持矢量字体（常见于 Anaconda），\n"
                            "请改用系统 Python 或安装 conda-forge 的 xft 版 tk。",
    },
    'en': {
        'app_title': "File Search Tool",
        'menu_language': "Language",
        'search_folder': "Search Folder",
        'browse': "Browse…",
        'search_keywords': "Keywords",
        'search': "Search",
        'cancel': "Cancel",
        'hint': "Separate multiple keywords with spaces; double-click a field for history",
        'by_name': "By Name",
        'by_content': "By Content",
        'match_all': "Match All Keywords",
        'match_any': "Match Any Keyword",
        'compact': "Compact View",
        'results': "Results",
        'open_file': "Open File",
        'open_containing': "Open Containing Folder",
        'copy_path': "Copy Path",
        'copy_item': "Copy File/Folder",
        'ready': "Ready",
        'font': "Font",
        'col_name': "Name",
        'col_path': "Path",
        'col_size': "Size",
        'col_date': "Modified",
        'font_size_status': "Font size: {size}",
        'error': "Error",
        'warning': "Warning",
        'notice': "Notice",
        'invalid_folder': "Invalid folder path: {path}",
        'enter_keywords': "Please enter search keywords",
        'enter_valid_keywords': "Please enter valid search keywords",
        'searching': "Searching for: {keywords}...",
        'searching_progress': "Searching... {count} results found",
        'mode_all': "all keywords",
        'mode_any': "any keyword",
        'search_done': "Search complete: {count} results matching {mode}",
        'search_error_status': "Search error: {error}",
        'search_error_msg': "An error occurred during search: {error}",
        'search_cancelled': "Search cancelled",
        'cannot_open_file': "Cannot open file: {error}",
        'cannot_open_folder': "Cannot open folder: {error}",
        'copied_path': "Copied path: {path}",
        'copied_paths': "Copied {count} paths",
        'cannot_copy_path': "Cannot copy path: {error}",
        'no_valid_paths': "No valid file paths",
        'copied_file': "✅ Copied file: {name}",
        'copied_folder': "✅ Copied folder: {name}",
        'copied_mixed': "✅ Copied {files} files and {folders} folders",
        'copied_files': "✅ Copied {files} files",
        'copied_folders': "✅ Copied {folders} folders",
        'copied_path_text': "Copied paths as plain text",
        'copy_failed_status': "❌ Copy failed: {error}",
        'copy_failed': "❌ Copy failed",
        'copy_error': "Copy operation error: {error}",
        'pyobjc_ask': "Cannot copy files to the clipboard (pyobjc may be required).\n"
                      "File paths were copied as plain text instead.\n\n"
                      "Show instructions for installing pyobjc?",
        'pyobjc_howto_title': "Installation",
        'pyobjc_howto': "Run the following command in a terminal to install pyobjc:\n\n"
                        "pip install pyobjc-framework-Cocoa\n\n"
                        "or with pip3:\n"
                        "pip3 install pyobjc-framework-Cocoa\n\n"
                        "Restart the app afterwards for full clipboard support.",
        'sort_error': "Sort error: {error}",
        'cjk_font_missing': "No Chinese font detected; Chinese text will show as boxes.\n\n"
                            "Install one by running in a terminal:\n"
                            "sudo apt install fonts-noto-cjk\n\n"
                            "Then restart this application.\n\n"
                            "Diagnostics: current font {font}, {count} fonts visible to Tk.\n"
                            "If Chinese fonts are installed but this count is small, "
                            "this Python's Tk lacks vector font support (common with Anaconda);\n"
                            "use the system Python or install the xft build of tk from conda-forge.",
    },
}


class FileSearchApp:
    def __init__(self, root):
        self.root = root
        self.config_file = os.path.join(os.path.expanduser("~"), ".file_search_config.json")
        # 语言需要在创建任何控件之前确定
        self.language = self._load_language()
        self.root.title(self.t('app_title'))
        self.root.geometry("920x640")
        self.root.minsize(780, 520)

        # Font configuration with platform-specific optimizations
        if sys.platform.startswith('linux'):
            # Linux: Prefer Noto Sans CJK SC for excellent Chinese character support
            # Fallback chain optimized for Chinese + English mixed text
            default_font_size = 13  # Slightly smaller for better fit

            # Tk silently substitutes missing fonts, so Font(...).actual() can't
            # detect availability — check against the real installed family list
            import tkinter.font as tkFont
            all_families = list(tkFont.families(root))
            available_families = {f.lower(): f for f in all_families}

            def pick(candidates):
                for name in candidates:
                    if name.lower() in available_families:
                        return available_families[name.lower()]
                return None

            # 现代矢量中文字体（中英文都能渲染好）
            cjk_candidates = [
                "Noto Sans CJK SC",      # Best for Chinese characters
                "Noto Sans SC",
                "Source Han Sans SC",
                "Source Han Sans CN",
                "WenQuanYi Micro Hei",   # Alternative Chinese font
                "WenQuanYi Zen Hei",
                "AR PL UMing CN",
                "Droid Sans Fallback",
            ]
            default_font_family = pick(cjk_candidates)
            if default_font_family is None:
                # 兜底：只按现代矢量中文字体的命名特征扫描；
                # 不能用 song/ming/kai/hei 这类短词，会误匹配 X11 位图字体
                # （如 "song ti"、"fangsong ti"），整套界面会变成像素点阵风格
                markers = ("cjk", "wenquanyi", "wqy", "micro hei", "zen hei", "source han")
                default_font_family = next(
                    (f for f in all_families if any(m in f.lower() for m in markers)), None)
            if default_font_family is None:
                # 没有可用的中文字体：退回高质量西文矢量字体，保证英文界面正常；
                # 界面搭好后再用弹窗提醒（GUI 方式启动时终端输出用户看不到）
                self._cjk_font_missing = True
                print("警告：未检测到中文字体，界面中文可能显示为方块。"
                      "建议安装：sudo apt install fonts-noto-cjk")
                default_font_family = pick(["Ubuntu", "Noto Sans", "DejaVu Sans",
                                            "Liberation Sans"]) or "Sans"
            self._font_diag = (default_font_family, len(all_families))
            print(f"Using font: {default_font_family}")
        elif sys.platform == "darwin":
            # macOS: 苹方字体，中英文混排显示效果更好
            default_font_family = "PingFang SC"
            default_font_size = 13
        else:
            # Windows and others: Use Arial
            default_font_family = "Arial"
            default_font_size = 12

        # 存储字体相关的变量
        self.default_font_family = default_font_family
        self.base_font_size = default_font_size  # 基础字体大小（根据系统）
        self.current_font_size = default_font_size  # 当前字体大小（用户可调整）

        self.default_font = (default_font_family, default_font_size)
        self.hint_font = (default_font_family, max(9, default_font_size - 2))
        # Slightly larger font for control area labels
        self.control_font = (default_font_family, default_font_size + 1)
        # 表头加粗字体
        self.heading_font = (default_font_family, default_font_size, "bold")

        # Apply font to all widgets
        self.root.option_add("*Font", self.default_font)
        
        # 设置窗口图标
        self.set_window_icon()
        
        # 配置文件路径已在 __init__ 开头设置（语言加载需要先读配置）

        # 搜索历史记录（最多10条）
        self.search_history = []
        
        # 设置暗色主题颜色（分层配色：窗口 < 表面 < 输入框 < 按钮）
        self.bg_color = "#1e1f22"        # 窗口背景（最深）
        self.surface_color = "#2b2d31"   # 表格/状态栏等表面背景
        self.entry_bg = "#313338"        # 输入框背景
        self.stripe_bg = "#36393f"       # 表格斑马纹
        self.border_color = "#3f4147"    # 边框
        self.accent_color = "#4e8cff"    # 蓝色强调色
        self.accent_hover = "#6ba1ff"    # 强调色（悬停）
        self.accent_pressed = "#3d74d9"  # 强调色（按下）
        self.text_color = "#e8eaed"      # 主文字
        self.muted_text = "#9aa0a6"      # 次要文字
        self.button_bg = "#3a3d42"       # 按钮背景
        self.button_hover = "#4a4e57"    # 按钮悬停
        self.button_text_color = self.text_color
        self.root.configure(bg=self.bg_color)
        
        # 搜索状态控制
        self.is_searching = False
        self.search_thread = None
        
        # 创建主框架
        self.main_frame = tk.Frame(root, bg=self.bg_color)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # 顶部控制卡片：把搜索表单和选项收进同一块面板，视觉上更聚拢
        self.card_frame = tk.Frame(self.main_frame, bg=self.surface_color, padx=12, pady=8,
                                   highlightbackground=self.border_color, highlightthickness=1)
        self.card_frame.pack(fill=tk.X)

        # 创建表单区域（网格布局：标签右对齐，输入框随窗口拉伸）
        self.form_frame = tk.Frame(self.card_frame, bg=self.surface_color)
        self.form_frame.pack(fill=tk.X)
        self.form_frame.columnconfigure(1, weight=1)

        # 文件夹选择
        self.folder_label = tk.Label(self.form_frame, text=self.t('search_folder'), bg=self.surface_color, fg=self.text_color, font=self.control_font)
        self.folder_label.grid(row=0, column=0, sticky="e", padx=(2, 10), pady=4)

        self.folder_var = tk.StringVar()

        # 初始化紧凑显示变量（需要在加载配置前创建）
        self.compact_display = tk.BooleanVar(value=False)

        # 加载上次保存的路径和设置
        self.load_config()

        style = ttk.Style()
        style.theme_use('clam')

        # Configure default font for all widgets
        style.configure('.', font=self.default_font, background=self.bg_color, foreground=self.text_color)

        # 普通按钮样式（圆角背景由图片元素绘制，见 _setup_rounded_styles）
        style.configure('Dark.TButton',
                        font=self.default_font,
                        background=self.surface_color,
                        foreground=self.text_color,
                        anchor='center',
                        relief='flat',
                        padding=(10, 2))

        # 小尺寸按钮样式（字体 +/- 按钮）
        style.configure('DarkSmall.TButton',
                        font=self.default_font,
                        background=self.surface_color,
                        foreground=self.text_color,
                        anchor='center',
                        relief='flat',
                        padding=(3, 0))

        # 强调按钮样式（搜索按钮）
        style.configure('Accent.TButton',
                        font=self.default_font,
                        background=self.surface_color,
                        foreground="#ffffff",
                        anchor='center',
                        relief='flat',
                        padding=(14, 2))

        # clam 主题的根样式会在 hover/按下时把控件背景变亮，
        # 从圆角图片的透明四角露出浅色方角——这里显式钉住背景色覆盖它
        for btn_style in ('Dark.TButton', 'DarkSmall.TButton', 'Accent.TButton'):
            style.map(btn_style,
                      background=[('pressed', self.surface_color),
                                  ('active', self.surface_color),
                                  ('disabled', self.surface_color)])

        # 单选按钮 / 复选框样式
        for option_style in ('Dark.TRadiobutton', 'Dark.TCheckbutton'):
            style.configure(option_style,
                            font=self.default_font,
                            background=self.surface_color,
                            foreground=self.text_color,
                            indicatorbackground=self.entry_bg,
                            indicatorforeground="#ffffff",
                            focuscolor=self.surface_color,
                            padding=(2, 2))
            style.map(option_style,
                      background=[('active', self.surface_color)],
                      foreground=[('active', self.accent_hover)],
                      indicatorbackground=[('selected', self.accent_color), ('active', self.button_hover)])

        # 分隔线与滚动条样式
        style.configure('TSeparator', background=self.border_color)
        for orient in ('Vertical', 'Horizontal'):
            style.configure(f'Dark.{orient}.TScrollbar',
                            background=self.button_bg,
                            troughcolor=self.bg_color,
                            bordercolor=self.bg_color,
                            lightcolor=self.button_bg,
                            darkcolor=self.button_bg,
                            arrowcolor=self.muted_text,
                            relief='flat')
            style.map(f'Dark.{orient}.TScrollbar',
                      background=[('active', self.button_hover)],
                      arrowcolor=[('active', self.text_color)])

        # Configure TCombobox with explicit font for better rendering
        # （圆角输入框背景由图片元素绘制，见 _setup_rounded_styles）
        style.configure('Dark.TCombobox',
                       font=self.default_font,
                       fieldbackground=self.entry_bg,
                       background=self.surface_color,
                       foreground=self.text_color,
                       arrowcolor=self.muted_text,
                       insertcolor=self.text_color,
                       padding=(6, 2))
        style.map('Dark.TCombobox',
                 background=[('pressed', self.surface_color),
                             ('active', self.surface_color),
                             ('focus', self.surface_color),
                             ('readonly', self.surface_color)],
                 fieldbackground=[('readonly', self.entry_bg)],
                 selectbackground=[('readonly', self.accent_color)],
                 selectforeground=[('readonly', self.text_color)],
                 arrowcolor=[('active', self.accent_color)])

        # 用图片元素实现圆角按钮 / 圆角输入框
        self._setup_rounded_styles(style)

        # 设置下拉列表字体和配色
        self.root.option_add('*TCombobox*Listbox.font', self.default_font)
        self.root.option_add('*TCombobox*Listbox.background', self.entry_bg)
        self.root.option_add('*TCombobox*Listbox.foreground', self.text_color)
        self.root.option_add('*TCombobox*Listbox.selectBackground', self.accent_color)
        self.root.option_add('*TCombobox*Listbox.selectForeground', "#ffffff")

        self.folder_entry = ttk.Combobox(self.form_frame, textvariable=self.folder_var, style='Dark.TCombobox', font=self.default_font)
        self.folder_entry.grid(row=0, column=1, sticky="ew", pady=4)
        # 添加双击事件绑定，双击空白区域显示下拉选项
        self.folder_entry.bind("<Double-Button-1>", self.show_folder_history)
        # 添加回车键绑定，按回车时添加到历史记录
        self.folder_entry.bind("<Return>", self.on_folder_entry_return)
        # 添加Esc键绑定，按Esc键退出焦点
        self.folder_entry.bind("<Escape>", self.on_escape_key)
        # 禁用滚轮切换选项
        self.folder_entry.bind("<MouseWheel>", lambda e: "break")
        self.folder_entry.bind("<Button-4>", lambda e: "break")
        self.folder_entry.bind("<Button-5>", lambda e: "break")
        
        # 加载文件夹历史
        self.load_folder_history()

        self.browse_button = ttk.Button(self.form_frame, text=self.t('browse'), command=self.browse_folder,
                                        style='Dark.TButton', cursor="hand2")
        self.browse_button.grid(row=0, column=2, padx=(10, 2), pady=4, sticky="ew")

        # 搜索关键词
        self.search_label = tk.Label(self.form_frame, text=self.t('search_keywords'), bg=self.surface_color, fg=self.text_color, font=self.control_font)
        self.search_label.grid(row=1, column=0, sticky="e", padx=(2, 10), pady=4)

        self.search_var = tk.StringVar()

        # 将Entry改为Combobox以支持历史记录
        self.search_entry = ttk.Combobox(self.form_frame, textvariable=self.search_var, style='Dark.TCombobox', font=self.default_font)
        self.search_entry.grid(row=1, column=1, sticky="ew", pady=4)
        self.search_entry.bind("<Return>", lambda event: self.search_files())
        # 添加双击事件绑定，双击空白区域显示下拉选项
        self.search_entry.bind("<Double-Button-1>", self.show_search_history)
        # 添加Esc键绑定，按Esc键退出焦点
        self.search_entry.bind("<Escape>", self.on_escape_key)
        # 禁用滚轮切换选项
        self.search_entry.bind("<MouseWheel>", lambda e: "break")
        self.search_entry.bind("<Button-4>", lambda e: "break")
        self.search_entry.bind("<Button-5>", lambda e: "break")
        
        # 加载搜索历史
        self.load_search_history()

        # 搜索按钮（与浏览按钮同列对齐；搜索状态由按钮文字和状态栏提示）
        self.search_button = ttk.Button(self.form_frame, text=self.t('search'), command=self.search_files,
                                        style='Accent.TButton', cursor="hand2")
        self.search_button.grid(row=1, column=2, padx=(10, 2), pady=4, sticky="ew")

        # 添加提示标签
        self.hint_label = tk.Label(self.form_frame, text=self.t('hint'),
                                 bg=self.surface_color, fg=self.muted_text, font=self.hint_font)
        self.hint_label.grid(row=2, column=1, sticky="w", pady=(0, 2))
        
        # 创建搜索选项框架（放在卡片内）
        self.option_frame = tk.Frame(self.card_frame, bg=self.surface_color)
        self.option_frame.pack(fill=tk.X, pady=(6, 0))

        # 搜索选项
        self.search_option = tk.StringVar()
        self.search_option.set("name")

        self.name_radio = ttk.Radiobutton(self.option_frame, text=self.t('by_name'), variable=self.search_option,
                                          value="name", style='Dark.TRadiobutton', cursor="hand2")
        self.name_radio.pack(side=tk.LEFT, padx=(2, 10))

        self.content_radio = ttk.Radiobutton(self.option_frame, text=self.t('by_content'), variable=self.search_option,
                                             value="content", style='Dark.TRadiobutton', cursor="hand2")
        self.content_radio.pack(side=tk.LEFT, padx=(0, 10))

        self.option_separator1 = ttk.Separator(self.option_frame, orient=tk.VERTICAL)
        self.option_separator1.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=4)

        # 匹配模式选项
        self.match_mode = tk.StringVar()
        self.match_mode.set("all")

        self.all_radio = ttk.Radiobutton(self.option_frame, text=self.t('match_all'), variable=self.match_mode,
                                         value="all", style='Dark.TRadiobutton', cursor="hand2")
        self.all_radio.pack(side=tk.LEFT, padx=(10, 10))

        self.any_radio = ttk.Radiobutton(self.option_frame, text=self.t('match_any'), variable=self.match_mode,
                                         value="any", style='Dark.TRadiobutton', cursor="hand2")
        self.any_radio.pack(side=tk.LEFT, padx=(0, 10))

        self.option_separator2 = ttk.Separator(self.option_frame, orient=tk.VERTICAL)
        self.option_separator2.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=4)

        # 添加紧凑显示选项 checkbox
        self.compact_check = ttk.Checkbutton(self.option_frame, text=self.t('compact'), variable=self.compact_display,
                                             style='Dark.TCheckbutton', cursor="hand2",
                                             command=self.toggle_compact_display)
        self.compact_check.pack(side=tk.LEFT, padx=(10, 5))

        # 禁用所有单选按钮和复选框的滚轮事件
        def block_scroll(event):
            return "break"

        for widget in [self.name_radio, self.content_radio, self.all_radio, self.any_radio, self.compact_check]:
            widget.bind("<MouseWheel>", block_scroll)
            widget.bind("<Button-4>", block_scroll)
            widget.bind("<Button-5>", block_scroll)

        
        # 创建结果框架
        self.result_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.result_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 6))

        # 结果标签
        self.result_label = tk.Label(self.result_frame, text=self.t('results'), bg=self.bg_color, anchor="w", fg=self.text_color, font=self.control_font)
        self.result_label.pack(fill=tk.X, pady=(0, 4))

        # Configure Treeview style with explicit font for better rendering on Linux
        # Calculate row height based on font size for proper spacing
        # 稀疏显示（默认）和紧凑显示的行高
        self.sparse_row_height = max(30, int(default_font_size * 2.3))  # 稀疏显示
        self.compact_row_height = max(20, int(default_font_size * 1.4))  # 紧凑显示
        current_row_height = self.sparse_row_height

        style.configure('Dark.Treeview',
                       background=self.surface_color,
                       foreground=self.text_color,
                       fieldbackground=self.surface_color,
                       bordercolor=self.border_color,
                       lightcolor=self.surface_color,
                       darkcolor=self.surface_color,
                       borderwidth=0,
                       relief='flat',
                       font=self.default_font,
                       rowheight=current_row_height)
        style.configure('Dark.Treeview.Heading',
                       background=self.bg_color,
                       foreground=self.muted_text,
                       borderwidth=0,
                       font=self.heading_font,
                       padding=(8, 6),
                       relief='flat')
        style.map('Dark.Treeview',
                 background=[('selected', self.accent_color)],
                 foreground=[('selected', '#ffffff')])
        style.map('Dark.Treeview.Heading',
                 background=[('active', self.button_hover)],
                 foreground=[('active', self.text_color)])
        
        # 添加排序状态跟踪
        self.sort_column = None
        self.sort_reverse = False

        # 创建表格显示结果（包含隐藏的完整路径列）
        # 列 ID 固定用中文（内部标识，不随语言变化），标题文字通过 t() 翻译
        self.all_columns = ("文件名", "路径", "完整路径", "大小", "修改日期")
        self.visible_columns = ("文件名", "路径", "大小", "修改日期")
        self.column_keys = {"文件名": 'col_name', "路径": 'col_path',
                            "大小": 'col_size', "修改日期": 'col_date'}
        self.result_tree = ttk.Treeview(self.result_frame, columns=self.all_columns, show="headings",
                                        style='Dark.Treeview', selectmode="extended", height=8)

        # 隐藏"完整路径"列（宽度设为0）
        self.result_tree.column("完整路径", width=0, stretch=False)

        # 设置列标题并绑定点击事件（只对可见列）
        for col in self.visible_columns:
            self.result_tree.heading(col, text=self.t(self.column_keys[col]),
                                     command=lambda c=col: self.sort_by_column(c))
            
        # 设置列宽（总宽控制在默认窗口内，避免一打开就出现横向滚动条）
        self.result_tree.column("文件名", width=250)
        self.result_tree.column("路径", width=320)
        self.result_tree.column("大小", width=90, anchor="e")
        self.result_tree.column("修改日期", width=170)

        # 斑马纹与文件夹行配色
        self.result_tree.tag_configure('even', background=self.surface_color)
        self.result_tree.tag_configure('odd', background=self.stripe_bg)
        self.result_tree.tag_configure('folder', foreground='#8ab4f8')

        # 添加滚动条
        self.scrollbar_y = ttk.Scrollbar(self.result_frame, orient=tk.VERTICAL, command=self.result_tree.yview,
                                         style='Dark.Vertical.TScrollbar')
        self.result_tree.configure(yscrollcommand=self.scrollbar_y.set)

        self.scrollbar_x = ttk.Scrollbar(self.result_frame, orient=tk.HORIZONTAL, command=self.result_tree.xview,
                                         style='Dark.Horizontal.TScrollbar')
        self.result_tree.configure(xscrollcommand=self.scrollbar_x.set)
        
        # 放置表格和滚动条
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定双击事件
        self.result_tree.bind("<Double-1>", self.open_file)

        # 绑定鼠标滚轮滚动（macOS 的 delta 是小步值，Windows 是 120 的倍数）
        def on_mousewheel(event):
            if sys.platform == "darwin":
                step = -event.delta
            else:
                step = int(-event.delta / 120)
            if step:
                self.result_tree.yview_scroll(step, "units")
            return "break"  # 阻止类默认绑定重复滚动
        self.result_tree.bind("<MouseWheel>", on_mousewheel)
        # Linux 滚轮支持
        self.result_tree.bind("<Button-4>", lambda e: self.result_tree.yview_scroll(-3, "units"))
        self.result_tree.bind("<Button-5>", lambda e: self.result_tree.yview_scroll(3, "units"))

        # 添加右键菜单绑定
        self.result_tree.bind("<Button-2>", self.show_context_menu)  # macOS右键
        self.result_tree.bind("<Control-Button-1>", self.show_context_menu)  # macOS Ctrl+左键
        self.result_tree.bind("<Button-3>", self.show_context_menu)  # Linux/Windows右键
        
        # 创建右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0, bg=self.surface_color, fg=self.text_color,
                                   activebackground=self.accent_color, activeforeground="#ffffff",
                                   font=self.default_font)
        self.context_menu.add_command(label=self.t('open_file'), command=self.open_selected_file)
        self.context_menu.add_command(label=self.t('open_containing'), command=self.open_containing_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=self.t('copy_path'), command=self.copy_file_path)
        self.context_menu.add_command(label=self.t('copy_item'), command=self.copy_file_or_folder)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set(self.t('ready'))
        # 状态栏容器（左侧状态信息，右侧字体大小调节）
        # before=result_frame 让状态栏优先于结果区分配空间，避免窗口不够高时被挤掉
        self.status_frame = tk.Frame(self.main_frame, bg=self.surface_color)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, before=self.result_frame)

        self.status_bar = tk.Label(self.status_frame, textvariable=self.status_var,
                                 bd=0, relief=tk.FLAT, anchor=tk.W, bg=self.surface_color, fg=self.muted_text,
                                 font=self.default_font, padx=10, pady=3)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 字体大小调整按钮（放在状态栏右侧，空间充裕不会被挤掉）
        self.increase_font_button = ttk.Button(self.status_frame, text="+", command=self.increase_font_size,
                                               style='DarkSmall.TButton', cursor="hand2", width=2)
        self.increase_font_button.pack(side=tk.RIGHT, padx=(2, 8), pady=3)

        self.decrease_font_button = ttk.Button(self.status_frame, text="−", command=self.decrease_font_size,
                                               style='DarkSmall.TButton', cursor="hand2", width=2)
        self.decrease_font_button.pack(side=tk.RIGHT, padx=2, pady=3)

        self.font_size_label = tk.Label(self.status_frame, text=self.t('font'), bg=self.surface_color,
                                        fg=self.muted_text, font=self.hint_font)
        self.font_size_label.pack(side=tk.RIGHT, padx=(10, 4))

        # 窗口内的语言切换按钮（macOS 的菜单栏在屏幕顶部，不易发现，这里再放一个入口）
        self.language_button = ttk.Button(self.status_frame, text=self._other_language_label(),
                                          command=self.toggle_language,
                                          style='DarkSmall.TButton', cursor="hand2", width=4)
        self.language_button.pack(side=tk.RIGHT, padx=(10, 4), pady=3)
        
        # 存储搜索结果
        self.search_results = []

        # 菜单栏：语言切换（中文/English）
        self.language_var = tk.StringVar(value=self.language)
        self.menubar = tk.Menu(self.root, tearoff=0)
        self.language_menu = tk.Menu(self.menubar, tearoff=0, bg=self.surface_color, fg=self.text_color,
                                     activebackground=self.accent_color, activeforeground="#ffffff")
        self.language_menu.add_radiobutton(label="中文", variable=self.language_var, value="zh",
                                           command=lambda: self.set_language("zh"))
        self.language_menu.add_radiobutton(label="English", variable=self.language_var, value="en",
                                           command=lambda: self.set_language("en"))
        self.menubar.add_cascade(label=self.t('menu_language'), menu=self.language_menu)
        # 只在 macOS 上挂菜单栏（显示在屏幕顶部系统栏）；
        # Linux/Windows 上 Tk 菜单栏会在窗口内占一条且不跟随暗色主题，
        # 这两个平台改用状态栏的"中文/EN"按钮切换
        if sys.platform == "darwin":
            self.root.config(menu=self.menubar)

        # 缺中文字体时弹窗提醒（延迟到主窗口显示后，GUI 启动时终端警告用户看不到）
        if getattr(self, '_cjk_font_missing', False):
            diag_font, diag_count = getattr(self, '_font_diag', ('?', 0))
            self.root.after(300, lambda: messagebox.showwarning(
                self.t('warning'),
                self.t('cjk_font_missing', font=diag_font, count=diag_count)))

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 绑定 Cmd+Plus / Cmd+Minus 快捷键调整字体大小
        self.root.bind("<Command-equal>", lambda e: self.increase_font_size())   # Cmd+=  (即 Cmd++)
        self.root.bind("<Command-plus>", lambda e: self.increase_font_size())    # Cmd++  (小键盘)
        self.root.bind("<Command-minus>", lambda e: self.decrease_font_size())   # Cmd+-

        # 应用保存的紧凑显示设置
        self.toggle_compact_display()

        # 应用加载的字体大小设置（如果与默认值不同）
        if self.current_font_size != self.base_font_size:
            self.update_all_fonts(self.current_font_size)
    
    def t(self, key, **kwargs):
        """按当前语言取界面文案，支持 {name} 形式的格式化参数"""
        text = TRANSLATIONS.get(self.language, TRANSLATIONS['zh']).get(key)
        if text is None:
            text = TRANSLATIONS['zh'].get(key, key)
        return text.format(**kwargs) if kwargs else text

    def _load_language(self):
        """在创建控件前从配置文件读取界面语言"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                lang = json.load(f).get('language', 'zh')
                return lang if lang in TRANSLATIONS else 'zh'
        except Exception:
            return 'zh'

    def set_language(self, lang):
        """切换界面语言并保存到配置"""
        if lang not in TRANSLATIONS or lang == self.language:
            return
        self.language = lang
        self.language_var.set(lang)
        self.apply_language()
        self.save_config()

    def toggle_language(self):
        """在中英文之间切换"""
        self.set_language('en' if self.language == 'zh' else 'zh')

    def _other_language_label(self):
        """窗口内切换按钮显示目标语言的名称"""
        return "EN" if self.language == 'zh' else "中文"

    def apply_language(self):
        """按当前语言刷新所有界面文案"""
        t = self.t
        self.root.title(t('app_title'))
        self.folder_label.config(text=t('search_folder'))
        self.browse_button.config(text=t('browse'))
        self.search_label.config(text=t('search_keywords'))
        self.search_button.config(text=t('cancel') if self.is_searching else t('search'))
        self.hint_label.config(text=t('hint'))
        self.name_radio.config(text=t('by_name'))
        self.content_radio.config(text=t('by_content'))
        self.all_radio.config(text=t('match_all'))
        self.any_radio.config(text=t('match_any'))
        self.compact_check.config(text=t('compact'))
        self.result_label.config(text=t('results'))
        self.font_size_label.config(text=t('font'))
        for col, key in self.column_keys.items():
            self.result_tree.heading(col, text=t(key))
        for index, key in enumerate(('open_file', 'open_containing', None, 'copy_path', 'copy_item')):
            if key:
                self.context_menu.entryconfigure(index, label=t(key))
        self.menubar.entryconfigure(self.menubar.index('end'), label=t('menu_language'))
        self.language_button.config(text=self._other_language_label())
        if not self.is_searching:
            self.status_var.set(t('ready'))

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                    # 加载最后的文件夹路径
                    try:
                        last_folder = config.get('last_folder', os.getcwd())
                        if os.path.isdir(last_folder):
                            self.folder_var.set(last_folder)
                        else:
                            self.folder_var.set(os.getcwd())
                    except Exception as e:
                        print(f"加载文件夹路径出错: {str(e)}")
                        self.folder_var.set(os.getcwd())

                    # 加载搜索历史
                    try:
                        self.search_history = config.get('search_history', [])
                        if not isinstance(self.search_history, list):
                            self.search_history = []
                    except Exception as e:
                        print(f"加载搜索历史出错: {str(e)}")
                        self.search_history = []

                    # 加载文件夹路径历史
                    try:
                        self.folder_history = config.get('folder_history', [])
                        if not isinstance(self.folder_history, list):
                            self.folder_history = []
                    except Exception as e:
                        print(f"加载文件夹历史出错: {str(e)}")
                        self.folder_history = []

                    # 加载紧凑显示设置
                    try:
                        compact_value = config.get('compact_display', False)
                        if isinstance(compact_value, bool):
                            self.compact_display.set(compact_value)
                    except Exception as e:
                        print(f"加载紧凑显示设置出错: {str(e)}")
                        self.compact_display.set(False)

                    # 加载字体大小设置
                    try:
                        font_size = config.get('font_size', self.base_font_size)
                        if isinstance(font_size, (int, float)) and 8 <= font_size <= 32:
                            self.current_font_size = int(font_size)
                        else:
                            self.current_font_size = self.base_font_size
                    except Exception as e:
                        print(f"加载字体大小设置出错: {str(e)}")
                        self.current_font_size = self.base_font_size
            else:
                self.folder_var.set(os.getcwd())
                self.search_history = []
                self.folder_history = []
        except Exception as e:
            print(f"加载配置文件出错: {str(e)}")
            self.folder_var.set(os.getcwd())
            self.search_history = []
            self.folder_history = []
    
    def save_config(self):
        """保存配置文件"""
        try:
            # 安全地获取所有配置值
            try:
                last_folder = self.folder_var.get()
            except:
                last_folder = os.getcwd()

            try:
                search_history = self.search_history if isinstance(self.search_history, list) else []
            except:
                search_history = []

            try:
                folder_history = self.folder_history if isinstance(self.folder_history, list) else []
            except:
                folder_history = []

            try:
                compact_display = self.compact_display.get()
            except:
                compact_display = False

            try:
                font_size = self.current_font_size
            except:
                font_size = self.base_font_size

            config = {
                'last_folder': last_folder,
                'search_history': search_history,
                'folder_history': folder_history,
                'compact_display': compact_display,
                'font_size': font_size,
                'language': self.language
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print("配置文件保存成功")
        except Exception as e:
            print(f"保存配置文件出错: {str(e)}")
    
    def show_folder_history(self, event):
        """双击文件夹输入框时显示历史记录下拉选项"""
        try:
            # 显示下拉列表
            self.folder_entry.event_generate('<Button-1>')
            self.folder_entry.event_generate('<Down>')
        except Exception as e:
            print(f"显示文件夹历史出错: {str(e)}")
    
    def load_folder_history(self):
        """加载文件夹历史到下拉框"""
        self.folder_entry['values'] = self.folder_history
    
    def add_to_folder_history(self, folder_path):
        """添加文件夹路径到历史记录"""
        if folder_path and folder_path.strip() and os.path.isdir(folder_path):
            folder_path = folder_path.strip()
            
            # 如果已存在，先移除
            if folder_path in self.folder_history:
                self.folder_history.remove(folder_path)
            
            # 添加到列表开头
            self.folder_history.insert(0, folder_path)
            
            # 保持最多10条记录
            if len(self.folder_history) > 10:
                self.folder_history = self.folder_history[:10]
            
            # 更新下拉框
            self.folder_entry['values'] = self.folder_history
            
            # 保存配置
            self.save_config()
    
    def on_folder_entry_return(self, event):
        """文件夹输入框按回车时的处理"""
        folder_path = self.folder_var.get()
        if folder_path:
            self.add_to_folder_history(folder_path)
    
    def on_escape_key(self, event):
        """按Esc键时退出输入框焦点"""
        try:
            # 将焦点转移到主窗口，从而退出当前输入框
            self.root.focus_set()
        except Exception as e:
            print(f"处理Esc键事件出错: {str(e)}")
    
    def show_search_history(self, event):
        """双击搜索框时显示历史记录下拉选项"""
        try:
            # 显示下拉列表
            self.search_entry.event_generate('<Button-1>')
            self.search_entry.event_generate('<Down>')
        except Exception as e:
            print(f"显示搜索历史出错: {str(e)}")
    
    def load_search_history(self):
        """加载搜索历史到下拉框"""
        self.search_entry['values'] = self.search_history
    
    def add_to_search_history(self, search_text):
        """添加搜索关键词到历史记录"""
        if search_text and search_text.strip():
            search_text = search_text.strip()
            
            # 如果已存在，先移除
            if search_text in self.search_history:
                self.search_history.remove(search_text)
            
            # 添加到列表开头
            self.search_history.insert(0, search_text)
            
            # 保持最多10条记录
            if len(self.search_history) > 10:
                self.search_history = self.search_history[:10]
            
            # 更新下拉框
            self.search_entry['values'] = self.search_history
            
            # 保存配置
            self.save_config()

    def toggle_compact_display(self):
        """切换紧凑/稀疏显示模式"""
        try:
            style = ttk.Style()

            if self.compact_display.get():
                # 切换到紧凑显示
                new_row_height = self.compact_row_height
            else:
                # 切换到稀疏显示
                new_row_height = self.sparse_row_height

            # 更新 Treeview 样式
            style.configure('Dark.Treeview', rowheight=new_row_height)

        except Exception as e:
            print(f"切换显示模式时出错: {str(e)}")

    def update_all_fonts(self, new_size):
        """更新所有组件的字体大小"""
        try:
            # 更新字体变量
            self.current_font_size = new_size
            self.default_font = (self.default_font_family, new_size)
            self.hint_font = (self.default_font_family, max(9, new_size - 2))
            self.control_font = (self.default_font_family, new_size + 1)
            self.heading_font = (self.default_font_family, new_size, "bold")

            # 更新全局字体设置
            self.root.option_add("*Font", self.default_font)

            # 更新各个 tk 组件的字体
            self.folder_label.config(font=self.control_font)
            self.search_label.config(font=self.control_font)
            self.hint_label.config(font=self.hint_font)
            self.font_size_label.config(font=self.hint_font)
            self.result_label.config(font=self.control_font)
            self.status_bar.config(font=self.default_font)

            # 直接更新 Combobox 控件字体（macOS 上 style 对输入区域不生效）
            self.folder_entry.config(font=self.default_font)
            self.search_entry.config(font=self.default_font)

            # 更新 ttk 样式（按钮、单选、复选、下拉框由样式统一控制字体）
            style = ttk.Style()
            style.configure('.', font=self.default_font)
            style.configure('Dark.TCombobox', font=self.default_font)
            style.configure('Dark.TButton', font=self.default_font)
            style.configure('DarkSmall.TButton', font=self.default_font)
            style.configure('Accent.TButton', font=self.default_font)
            style.configure('Dark.TRadiobutton', font=self.default_font)
            style.configure('Dark.TCheckbutton', font=self.default_font)
            self.root.option_add('*TCombobox*Listbox.font', self.default_font)

            # 重新计算行高
            self.sparse_row_height = max(30, int(new_size * 2.3))
            self.compact_row_height = max(20, int(new_size * 1.4))

            # 根据当前显示模式设置行高
            if self.compact_display.get():
                current_row_height = self.compact_row_height
            else:
                current_row_height = self.sparse_row_height

            style.configure('Dark.Treeview', font=self.default_font, rowheight=current_row_height)
            style.configure('Dark.Treeview.Heading', font=self.heading_font)

            # 更新右键菜单字体
            self.context_menu.config(font=self.default_font)

            # 保存配置
            self.save_config()

            print(f"字体大小已更新为: {new_size}")

        except Exception as e:
            print(f"更新字体大小时出错: {str(e)}")

    def increase_font_size(self):
        """增大字体"""
        new_size = min(32, self.current_font_size + 1)  # 最大32
        if new_size != self.current_font_size:
            self.update_all_fonts(new_size)
            self.status_var.set(self.t('font_size_status', size=new_size))
            self.root.after(2000, lambda: self.status_var.set(self.t('ready')))

    def decrease_font_size(self):
        """减小字体"""
        new_size = max(8, self.current_font_size - 1)  # 最小8
        if new_size != self.current_font_size:
            self.update_all_fonts(new_size)
            self.status_var.set(self.t('font_size_status', size=new_size))
            self.root.after(2000, lambda: self.status_var.set(self.t('ready')))

    def on_closing(self):
        """窗口关闭时的处理"""
        self.save_config()
        self.root.destroy()
    
    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_var.set(folder_selected)
            # 自动添加到历史记录
            self.add_to_folder_history(folder_selected)
    
    def parse_search_terms(self, search_text):
        """解析搜索关键词，支持空格分隔的多关键词"""
        # 去除首尾空格并按空格分割
        terms = [term.strip() for term in search_text.split() if term.strip()]
        return terms
    
    def match_keywords(self, text, keywords_lower, match_mode):
        """检查文本是否匹配关键词（keywords_lower 应该已经是小写的）"""
        text_lower = text.lower()

        if match_mode == "all":
            # 所有关键词都必须匹配
            return all(kw in text_lower for kw in keywords_lower)
        else:
            # 任一关键词匹配即可
            return any(kw in text_lower for kw in keywords_lower)

    def content_matches(self, path, keywords_lower, match_mode, file_size=None, chunk_size=4 * 1024 * 1024):
        """文件内容关键词匹配。

        小文件（不超过一个块）直接整读——f.read() 无参数走 CPython 快速路径；
        大文件分块读取：内存占用恒定、找到即提前返回，
        且每块之间释放 GIL，避免搜索大文件时界面卡顿。
        """
        if file_size is not None and file_size <= chunk_size:
            # utf-8 下字符数 <= 字节数，单块一定装得下
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return self.match_keywords(f.read(), keywords_lower, match_mode)
            except Exception:
                return False

        found = [False] * len(keywords_lower)
        # 块边界处保留最长关键词长度的重叠，避免关键词恰好跨块被漏掉
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
                    if len(chunk) < chunk_size:
                        break  # 不足一块说明已到文件末尾，省一次空读取
                    tail = chunk[-overlap:] if overlap > 0 else ""
        except Exception:
            return False
        return all(found) if match_mode == "all" else False
    
    def search_files_threaded(self):
        """在后台线程中执行搜索"""
        try:
            search_path = self.folder_var.get()
            search_text = self.search_var.get()
            search_type = self.search_option.get()
            match_mode = self.match_mode.get()
            
            if not os.path.isdir(search_path):
                self.root.after(0, lambda: messagebox.showerror(self.t('error'), self.t('invalid_folder', path=search_path)))
                return
            
            if not search_text:
                self.root.after(0, lambda: messagebox.showwarning(self.t('warning'), self.t('enter_keywords')))
                return
            
            # 解析搜索关键词
            keywords = self.parse_search_terms(search_text)
            if not keywords:
                self.root.after(0, lambda: messagebox.showwarning(self.t('warning'), self.t('enter_valid_keywords')))
                return
            
            # 预先计算小写关键词，避免重复转换
            keywords_lower = [kw.lower() for kw in keywords]
            
            self.root.after(0, lambda: self.status_var.set(self.t('searching', keywords=', '.join(keywords))))
            
            count = 0
            
            # 批量更新设置
            batch_results = []
            batch_size = 50  # 每50个结果更新一次UI
            last_update_time = 0
            update_interval = 0.1  # 至少每0.1秒更新一次
            
            def flush_batch():
                """将批量结果刷新到UI"""
                nonlocal batch_results
                if batch_results:
                    results_to_add = batch_results.copy()
                    batch_results = []
                    self.root.after(0, lambda r=results_to_add: self.add_batch_to_results(r))
            
            # 使用 os.scandir 进行快速递归遍历
            def make_row(entry, st, is_folder):
                """在工作线程中完成 stat 和格式化，避免占用界面线程做磁盘 IO"""
                mtime_str = datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                parent_path = os.path.dirname(entry.path)
                if is_folder:
                    return (f"📁 {entry.name}", parent_path, entry.path, "<文件夹>", mtime_str, True)
                size = st.st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.2f} KB"
                else:
                    size_str = f"{size/(1024*1024):.2f} MB"
                return (entry.name, parent_path, entry.path, size_str, mtime_str, False)

            def scan_directory(path):
                nonlocal count, batch_results, last_update_time

                if not self.is_searching:
                    return

                try:
                    with os.scandir(path) as entries:
                        dirs_to_scan = []

                        for entry in entries:
                            if not self.is_searching:
                                return

                            try:
                                if entry.is_dir(follow_symlinks=False):
                                    # 搜索文件夹名称（只在按文件名搜索时）
                                    if search_type == "name":
                                        if self.match_keywords(entry.name, keywords_lower, match_mode):
                                            batch_results.append(make_row(entry, entry.stat(follow_symlinks=False), True))
                                            count += 1

                                    # 记录需要继续扫描的目录
                                    dirs_to_scan.append(entry.path)

                                elif entry.is_file(follow_symlinks=False):
                                    # 按文件名搜索
                                    if search_type == "name":
                                        if self.match_keywords(entry.name, keywords_lower, match_mode):
                                            batch_results.append(make_row(entry, entry.stat(follow_symlinks=False), False))
                                            count += 1

                                    # 按内容搜索
                                    elif search_type == "content":
                                        try:
                                            # 快速检查文件大小，跳过超大文件
                                            st = entry.stat(follow_symlinks=False)
                                            if st.st_size > 100 * 1024 * 1024:  # 跳过大于100MB的文件
                                                continue

                                            # 小文件整读、大文件分块，避免长时间占用 GIL 卡住界面
                                            if self.content_matches(entry.path, keywords_lower, match_mode, st.st_size):
                                                batch_results.append(make_row(entry, st, False))
                                                count += 1
                                        except Exception:
                                            pass
                                
                                # 检查是否需要刷新批量结果
                                current_time = time.time()
                                if len(batch_results) >= batch_size or (current_time - last_update_time) > update_interval:
                                    flush_batch()
                                    last_update_time = current_time
                                    # 更新状态显示
                                    self.root.after(0, lambda c=count: self.status_var.set(self.t('searching_progress', count=c)))
                                    
                            except (PermissionError, OSError):
                                continue
                        
                        # 递归扫描子目录
                        for dir_path in dirs_to_scan:
                            if not self.is_searching:
                                return
                            scan_directory(dir_path)
                            
                except (PermissionError, OSError):
                    pass
            
            # 开始扫描
            last_update_time = time.time()
            scan_directory(search_path)
            
            # 刷新剩余的批量结果
            flush_batch()
            
            if self.is_searching:  # 只有在没有被取消的情况下才显示完成消息
                mode_text = self.t('mode_all') if match_mode == "all" else self.t('mode_any')
                self.root.after(0, lambda: self.status_var.set(self.t('search_done', count=count, mode=mode_text)))
        
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(self.t('search_error_status', error=str(e))))
            self.root.after(0, lambda: messagebox.showerror(self.t('error'), self.t('search_error_msg', error=str(e))))
        
        finally:
            # 搜索完成，重置状态
            self.is_searching = False
            self.root.after(0, lambda: self.search_button.config(text=self.t('search'), command=self.search_files))
    
    def search_files(self):
        if self.is_searching:
            # 如果正在搜索，则取消搜索
            self.is_searching = False
            self.search_button.config(text=self.t('search'), command=self.search_files)
            self.status_var.set(self.t('search_cancelled'))
            return
        
        # 获取搜索关键词并添加到历史记录
        search_text = self.search_var.get()
        if search_text and search_text.strip():
            self.add_to_search_history(search_text)
        
        # 清空之前的结果
        for i in self.result_tree.get_children():
            self.result_tree.delete(i)
        self.search_results = []

        # 开始新的搜索
        self.is_searching = True
        self.search_button.config(text=self.t('cancel'), command=self.search_files)

        # 在后台线程中执行搜索
        self.search_thread = threading.Thread(target=self.search_files_threaded, daemon=True)
        self.search_thread.start()
    
    def add_file_to_results(self, file_path):
        try:
            # 获取文件信息
            file_name = os.path.basename(file_path)
            parent_path = os.path.dirname(file_path)  # 父文件夹路径
            file_size = os.path.getsize(file_path)
            file_mtime = os.path.getmtime(file_path)

            # 格式化文件大小
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size/1024:.2f} KB"
            else:
                size_str = f"{file_size/(1024*1024):.2f} MB"

            # 格式化修改时间
            mtime_str = datetime.datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M:%S')

            # 添加到结果列表（含斑马纹标签）
            row_tag = 'odd' if len(self.search_results) % 2 else 'even'
            self.search_results.append(file_path)
            # 格式：文件名、父路径、完整路径（隐藏）、大小、修改日期
            self.result_tree.insert("", tk.END, values=(file_name, parent_path, file_path, size_str, mtime_str), tags=(row_tag,))

        except Exception as e:
            print(f"添加文件到结果时出错: {str(e)}")
    
    def add_folder_to_results(self, folder_path):
        try:
            # 获取文件夹信息
            folder_name = os.path.basename(folder_path)
            parent_path = os.path.dirname(folder_path)  # 父文件夹路径
            folder_mtime = os.path.getmtime(folder_path)

            # 格式化修改时间
            mtime_str = datetime.datetime.fromtimestamp(folder_mtime).strftime('%Y-%m-%d %H:%M:%S')

            # 添加到结果列表（含斑马纹标签）
            row_tag = 'odd' if len(self.search_results) % 2 else 'even'
            self.search_results.append(folder_path)
            # 格式：文件名、父路径、完整路径（隐藏）、大小、修改日期
            self.result_tree.insert("", tk.END, values=(f"📁 {folder_name}", parent_path, folder_path, "<文件夹>", mtime_str), tags=(row_tag, 'folder'))

        except Exception as e:
            print(f"添加文件夹到结果时出错: {str(e)}")
    
    def add_batch_to_results(self, batch):
        """批量添加结果到列表。

        stat/格式化已在工作线程完成（见 make_row），这里只做纯插入，
        避免界面线程做磁盘 IO 造成卡顿。
        """
        try:
            insert = self.result_tree.insert
            for display_name, parent_path, path, size_str, mtime_str, is_folder in batch:
                try:
                    # 斑马纹标签（按当前行数交替）
                    row_tag = 'odd' if len(self.search_results) % 2 else 'even'
                    tags = (row_tag, 'folder') if is_folder else (row_tag,)
                    self.search_results.append(path)
                    # 格式：文件名、父路径、完整路径（隐藏）、大小、修改日期
                    insert("", tk.END, values=(display_name, parent_path, path, size_str, mtime_str), tags=tags)
                except Exception as e:
                    print(f"添加结果时出错: {str(e)}")
        except Exception as e:
            print(f"批量添加结果时出错: {str(e)}")
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 选择右键点击的项
        item = self.result_tree.identify_row(event.y)
        if item:
            # 如果右键点在已选中的项目上，保留当前多选；否则只选中当前项
            current_selection = self.result_tree.selection()
            if item not in current_selection:
                self.result_tree.selection_set(item)
            self.result_tree.focus(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def open_selected_file(self):
        """打开选中的文件"""
        if not self.result_tree.selection():
            return

        selected_item = self.result_tree.selection()[0]
        file_path = self.result_tree.item(selected_item, "values")[2]  # 从完整路径列获取

        try:
            if sys.platform.startswith('linux'):
                subprocess.run(["xdg-open", file_path])
            elif sys.platform == "darwin":
                subprocess.run(["open", file_path])
            else:  # Windows
                os.startfile(file_path)
        except Exception as e:
            messagebox.showerror(self.t('error'), self.t('cannot_open_file', error=str(e)))
    
    def open_containing_folder(self):
        """打开文件所在的文件夹"""
        if not self.result_tree.selection():
            return

        selected_item = self.result_tree.selection()[0]
        file_path = self.result_tree.item(selected_item, "values")[2]  # 从完整路径列获取

        try:
            if sys.platform.startswith('linux'):
                # Linux: 使用文件管理器打开目录
                if os.path.isfile(file_path):
                    folder = os.path.dirname(file_path)
                    subprocess.run(["xdg-open", folder])
                else:
                    subprocess.run(["xdg-open", file_path])
            elif sys.platform == "darwin":
                # macOS: 可以高亮选中文件
                if os.path.isfile(file_path):
                    subprocess.run(["open", "-R", file_path])
                else:
                    subprocess.run(["open", file_path])
            else:  # Windows
                if os.path.isfile(file_path):
                    subprocess.run(["explorer", "/select,", file_path])
                else:
                    os.startfile(file_path)
        except Exception as e:
            messagebox.showerror(self.t('error'), self.t('cannot_open_folder', error=str(e)))
    
    def copy_file_path(self):
        """复制文件路径到剪贴板（支持多选）"""
        if not self.result_tree.selection():
            return

        selected_items = self.result_tree.selection()
        paths = [self.result_tree.item(i, "values")[2] for i in selected_items]  # 从完整路径列获取
        text_to_copy = "\n".join(paths)
        
        try:
            # 将路径（可能多条）复制到剪贴板
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            if len(paths) == 1:
                self.status_var.set(self.t('copied_path', path=paths[0]))
            else:
                self.status_var.set(self.t('copied_paths', count=len(paths)))
            # 添加定时器，3秒后清除状态信息
            self.root.after(3000, lambda: self.status_var.set(self.t('ready')))
        except Exception as e:
            messagebox.showerror(self.t('error'), self.t('cannot_copy_path', error=str(e)))
    
    def copy_file_or_folder(self):
        """复制选中的文件或文件夹到剪贴板（支持多选，Finder 可直接粘贴）"""
        if not self.result_tree.selection():
            return

        selected_items = self.result_tree.selection()
        file_paths = [self.result_tree.item(i, "values")[2] for i in selected_items]  # 从完整路径列获取
        
        try:
            # 验证所有文件都存在
            valid_paths = []
            for path in file_paths:
                if os.path.exists(path):
                    # 转换为绝对路径
                    valid_paths.append(os.path.abspath(path))
                else:
                    print(f"文件不存在: {path}")
            
            if not valid_paths:
                messagebox.showwarning(self.t('warning'), self.t('no_valid_paths'))
                return
            
            success = False
            error_msg = ""
            
            print(f"准备复制 {len(valid_paths)} 个文件/文件夹:")
            for path in valid_paths:
                print(f"  - {path}")
            
            # 方法1：尝试使用 pyobjc（如果已安装）
            try:
                from AppKit import NSPasteboard, NSURL
                
                print("🔄 使用 PyObjC 方法...")
                pb = NSPasteboard.generalPasteboard()
                pb.clearContents()
                
                # 创建 NSURL 对象数组
                urls = [NSURL.fileURLWithPath_(path) for path in valid_paths]
                
                # 写入剪贴板
                success = pb.writeObjects_(urls)
                
                if success:
                    print("✅ PyObjC 方法成功")
                    
            except ImportError:
                print("⚠️ pyobjc 未安装，尝试其他方法")
            except Exception as e:
                print(f"💥 PyObjC 方法异常: {e}")
            
            # 方法2：使用改进的 AppleScript
            if not success:
                try:
                    print("🔄 使用 AppleScript 复制文件...")
                    
                    if len(valid_paths) == 1:
                        # 单个文件 - 使用简单的方式
                        path = valid_paths[0]
                        # 使用 quoted form 来正确处理路径中的特殊字符
                        script = f'''
                        set thePath to POSIX file "{path.replace('"', '\\"')}"
                        tell application "Finder"
                            set the clipboard to (thePath as alias)
                        end tell
                        '''
                    else:
                        # 多个文件 - 构建文件列表
                        # 使用不同的方法：通过多个 osascript 调用来构建列表
                        script_lines = []
                        script_lines.append('tell application "Finder"')
                        script_lines.append('set fileList to {}')
                        
                        for path in valid_paths:
                            escaped_path = path.replace('\\', '\\\\').replace('"', '\\"')
                            script_lines.append(f'set end of fileList to (POSIX file "{escaped_path}" as alias)')
                        
                        script_lines.append('set the clipboard to fileList')
                        script_lines.append('end tell')
                        
                        script = '\n'.join(script_lines)
                    
                    # 执行 AppleScript
                    result = subprocess.run(
                        ['osascript', '-e', script],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        print("✅ AppleScript 方法成功")
                        success = True
                    else:
                        error_msg = result.stderr.strip() if result.stderr else "AppleScript 执行失败"
                        print(f"❌ AppleScript 失败: {error_msg}")
                        
                except subprocess.TimeoutExpired:
                    error_msg = "AppleScript 执行超时"
                    print("⏰ AppleScript 超时")
                except Exception as e:
                    error_msg = str(e)
                    print(f"💥 AppleScript 异常: {e}")
            
            # 方法3：使用文件 URL 方案
            if not success:
                try:
                    print("🔄 尝试文件 URL 方法...")
                    
                    # 创建一个包含所有文件路径的临时文件
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                        for path in valid_paths:
                            f.write(f"file://{quote(path)}\n")
                        temp_file = f.name
                    
                    # 使用 pbcopy 复制文件 URLs
                    with open(temp_file, 'rb') as f:
                        subprocess.run(['pbcopy'], stdin=f, check=True)
                    
                    # 删除临时文件
                    os.unlink(temp_file)
                    
                    print("✅ 文件 URL 方法成功")
                    success = True
                    error_msg = "已复制（URL格式）"
                    
                except Exception as e:
                    print(f"💥 文件 URL 方法异常: {e}")
            
            # 方法4：最简单的 AppleScript 方法（使用文件列表字符串）
            if not success:
                try:
                    print("🔄 尝试简化的 AppleScript 方法...")
                    
                    # 为每个文件创建独立的 alias，然后组合
                    if len(valid_paths) == 1:
                        # 单文件
                        path = valid_paths[0]
                        # 创建一个简单的脚本
                        result = subprocess.run([
                            'osascript',
                            '-e', f'tell application "Finder"',
                            '-e', f'set theFile to POSIX file "{path}" as alias',
                            '-e', f'set the clipboard to theFile',
                            '-e', f'end tell'
                        ], capture_output=True, text=True, timeout=10)
                        
                        if result.returncode == 0:
                            print("✅ 简化 AppleScript 方法成功（单文件）")
                            success = True
                    else:
                        # 多文件 - 使用序列化的 osascript 命令
                        commands = ['osascript']
                        commands.extend(['-e', 'tell application "Finder"'])
                        commands.extend(['-e', 'set fileList to {}'])
                        
                        for path in valid_paths:
                            # 确保路径没有问题的引号
                            safe_path = path.replace('"', '\\"').replace('$', '\\$')
                            commands.extend(['-e', f'set end of fileList to (POSIX file "{safe_path}" as alias)'])
                        
                        commands.extend(['-e', 'set the clipboard to fileList'])
                        commands.extend(['-e', 'end tell'])
                        
                        result = subprocess.run(commands, capture_output=True, text=True, timeout=10)
                        
                        if result.returncode == 0:
                            print("✅ 简化 AppleScript 方法成功（多文件）")
                            success = True
                        else:
                            error_msg = result.stderr.strip() if result.stderr else "执行失败"
                            print(f"❌ 错误: {error_msg}")
                            
                except Exception as e:
                    error_msg = str(e)
                    print(f"💥 简化 AppleScript 方法异常: {e}")
            
            # 最后的备用方案：复制路径文本
            if not success:
                try:
                    print("🔄 复制文件路径为文本...")
                    text_paths = "\n".join(valid_paths)
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text_paths)
                    print("✅ 已复制路径文本")
                    
                    # 提示用户
                    response = messagebox.askyesno(self.t('notice'), self.t('pyobjc_ask'))

                    if response:
                        messagebox.showinfo(self.t('pyobjc_howto_title'), self.t('pyobjc_howto'))
                    
                    success = True
                    error_msg = self.t('copied_path_text')
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ 文本复制也失败: {e}")
            
            # 状态提示
            if success and not error_msg:
                if len(valid_paths) == 1:
                    base = os.path.basename(valid_paths[0])
                    if os.path.isfile(valid_paths[0]):
                        self.status_var.set(self.t('copied_file', name=base))
                    else:
                        self.status_var.set(self.t('copied_folder', name=base))
                else:
                    file_count = sum(1 for p in valid_paths if os.path.isfile(p))
                    folder_count = len(valid_paths) - file_count
                    if file_count > 0 and folder_count > 0:
                        self.status_var.set(self.t('copied_mixed', files=file_count, folders=folder_count))
                    elif file_count > 0:
                        self.status_var.set(self.t('copied_files', files=file_count))
                    else:
                        self.status_var.set(self.t('copied_folders', folders=folder_count))
            elif success and error_msg:
                self.status_var.set(f"⚠️ {error_msg}")
            else:
                self.status_var.set(self.t('copy_failed_status', error=error_msg))
            
            # 5秒后清空状态
            self.root.after(5000, lambda: self.status_var.set(self.t('ready')))
            
        except Exception as e:
            error_message = self.t('copy_error', error=str(e))
            print(error_message)
            self.status_var.set(self.t('copy_failed'))
            messagebox.showerror(self.t('error'), error_message)
        
    def open_file(self, event):
        # 检查是否有选中的项
        if not self.result_tree.selection():
            return

        # 获取选中的项
        selected_item = self.result_tree.selection()[0]
        file_path = self.result_tree.item(selected_item, "values")[2]  # 从完整路径列获取

        try:
            # 使用平台特定的命令打开文件
            if sys.platform.startswith('linux'):
                subprocess.run(["xdg-open", file_path])
            elif sys.platform == "darwin":
                subprocess.run(["open", file_path])
            else:  # Windows
                os.startfile(file_path)
        except Exception as e:
            messagebox.showerror(self.t('error'), self.t('cannot_open_file', error=str(e)))

    def _round_rect_image(self, fill, outline=None, radius=8, size=26):
        """生成圆角矩形图片（4x 超采样抗锯齿，透明圆角外区域）"""
        scale = 4
        img = Image.new('RGBA', (size * scale, size * scale), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((0, 0, size * scale - 1, size * scale - 1),
                               radius=radius * scale, fill=fill,
                               outline=outline, width=scale if outline else 0)
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)

    def _chevron_image(self, color, size=20):
        """生成透明背景的下拉箭头图片"""
        scale = 4
        s = size * scale
        img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.line([(s * 0.30, s * 0.42), (s * 0.50, s * 0.62), (s * 0.70, s * 0.42)],
                  fill=color, width=int(s * 0.07), joint='curve')
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)

    def _setup_rounded_styles(self, style):
        """用图片元素给按钮和下拉输入框加上圆角外观"""
        # 保持引用，防止图片被垃圾回收
        self._round_images = {
            'btn': self._round_rect_image(self.button_bg, outline=self.border_color),
            'btn_hover': self._round_rect_image(self.button_hover, outline=self.accent_color),
            'btn_pressed': self._round_rect_image(self.accent_pressed),
            'accent': self._round_rect_image(self.accent_color),
            'accent_hover': self._round_rect_image(self.accent_hover),
            'accent_pressed': self._round_rect_image(self.accent_pressed),
            'field': self._round_rect_image(self.entry_bg, outline=self.border_color),
            'field_focus': self._round_rect_image(self.entry_bg, outline=self.accent_color),
            'arrow': self._chevron_image(self.muted_text),
            'arrow_active': self._chevron_image(self.accent_color),
        }

        # 注意：图片元素的 padding 默认等于 border（会把内容撑开 11px），
        # 这里显式指定小 padding 来压低控件高度
        style.element_create('RoundedDark.button', 'image', self._round_images['btn'],
                             ('pressed', self._round_images['btn_pressed']),
                             ('active', self._round_images['btn_hover']),
                             border=11, padding=(2, 2), sticky='nsew')
        style.element_create('RoundedAccent.button', 'image', self._round_images['accent'],
                             ('pressed', self._round_images['accent_pressed']),
                             ('active', self._round_images['accent_hover']),
                             border=11, padding=(2, 2), sticky='nsew')
        style.element_create('RoundedField.field', 'image', self._round_images['field'],
                             ('focus', self._round_images['field_focus']),
                             border=11, padding=(4, 2), sticky='nsew')
        # 元素名以 downarrow 结尾，才能命中 ttk::combobox 的点击展开判断
        style.element_create('Rounded.downarrow', 'image', self._round_images['arrow'],
                             ('active', self._round_images['arrow_active']),
                             sticky='')

        def rounded_button_layout(element):
            return [(element, {'sticky': 'nsew', 'children': [
                ('Button.padding', {'sticky': 'nsew', 'children': [
                    ('Button.label', {'sticky': 'nsew'})]})]})]

        style.layout('Dark.TButton', rounded_button_layout('RoundedDark.button'))
        style.layout('DarkSmall.TButton', rounded_button_layout('RoundedDark.button'))
        style.layout('Accent.TButton', rounded_button_layout('RoundedAccent.button'))

        style.layout('Dark.TCombobox', [
            ('RoundedField.field', {'sticky': 'nsew', 'children': [
                ('Rounded.downarrow', {'side': 'right', 'sticky': ''}),
                ('Combobox.padding', {'expand': '1', 'sticky': 'nsew', 'children': [
                    ('Combobox.textarea', {'sticky': 'nsew'})]})]})])

    def set_window_icon(self):
        """设置窗口图标"""
        # 打包后的 macOS .app 由 Info.plist 引用的 icns 提供高清图标，
        # iconphoto 会用位图覆盖它导致 Dock/Cmd+Tab 里变模糊，直接跳过
        if sys.platform == "darwin" and getattr(sys, "frozen", False):
            return
        try:
            # 图标文件路径（兼容打包后的应用）
            icon_path = resource_path(os.path.join("assets", "AppIcon.icns"))

            if os.path.exists(icon_path):
                image = Image.open(icon_path)
                # 提供多档尺寸由系统按显示场景选择，避免小图被放大导致模糊
                icons = [
                    ImageTk.PhotoImage(image.resize((size, size), Image.Resampling.LANCZOS))
                    for size in (512, 256, 128, 64, 32, 16)
                ]
                self.root.iconphoto(True, *icons)

                # 保持图片引用，防止被垃圾回收
                self.window_icon = icons
                print("窗口图标设置成功")
            else:
                print(f"图标文件不存在: {icon_path}")
        except Exception as e:
            print(f"设置窗口图标失败: {str(e)}")

    def sort_by_column(self, column):
        """根据指定列对结果进行排序"""
        try:
            # 获取所有行的数据
            data = []
            for child in self.result_tree.get_children():
                values = self.result_tree.item(child, 'values')
                data.append((child, values))
            
            if not data:
                return
            
            # 确定排序方向
            if self.sort_column == column:
                self.sort_reverse = not self.sort_reverse
            else:
                self.sort_column = column
                self.sort_reverse = False
            
            # 获取列索引（从所有列中查找）
            col_index = self.all_columns.index(column)

            # 定义排序键函数
            def sort_key(item):
                value = item[1][col_index]
                
                if column == "大小":
                    # 处理文件大小排序
                    if value == "<文件夹>":
                        return -1 if not self.sort_reverse else float('inf')
                    
                    # 解析文件大小
                    try:
                        if value.endswith(' B'):
                            return float(value[:-2])
                        elif value.endswith(' KB'):
                            return float(value[:-3]) * 1024
                        elif value.endswith(' MB'):
                            return float(value[:-3]) * 1024 * 1024
                        elif value.endswith(' GB'):
                            return float(value[:-3]) * 1024 * 1024 * 1024
                        else:
                            return 0
                    except:
                        return 0
                        
                elif column == "修改日期":
                    # 处理日期排序
                    try:
                        return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                    except:
                        return datetime.datetime.min
                        
                elif column == "文件名":
                    # 文件名排序，文件夹优先或文件优先
                    is_folder = value.startswith('📁 ')
                    name = value[2:] if is_folder else value
                    # 文件夹和文件分别排序，文件夹在前
                    return (0 if is_folder else 1, name.lower())
                    
                else:
                    # 默认字符串排序
                    return value.lower()
            
            # 执行排序
            data.sort(key=sort_key, reverse=self.sort_reverse)

            # 更新列标题显示排序指示器（只更新可见列）
            for col in self.visible_columns:
                heading_text = self.t(self.column_keys[col])
                if col == column:
                    indicator = " ↓" if self.sort_reverse else " ↑"
                    self.result_tree.heading(col, text=heading_text + indicator)
                else:
                    self.result_tree.heading(col, text=heading_text)
            
            # 重新排列树视图中的项目，并重新分配斑马纹
            # （用已取到的 values 判断文件夹，避免每行再读一次 tags）
            move = self.result_tree.move
            set_item = self.result_tree.item
            for index, (child, values) in enumerate(data):
                move(child, '', index)
                row_tag = 'odd' if index % 2 else 'even'
                if values[0].startswith('📁 '):
                    set_item(child, tags=(row_tag, 'folder'))
                else:
                    set_item(child, tags=(row_tag,))
                
        except Exception as e:
            print(f"排序时出错: {str(e)}")
            messagebox.showerror(self.t('error'), self.t('sort_error', error=str(e)))










def main():
    root = tk.Tk()
    app = FileSearchApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

