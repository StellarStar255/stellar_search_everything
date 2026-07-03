# macOS Python GUI 应用打包指南

本文档记录如何将 Python tkinter GUI 程序打包成 macOS 原生应用（.app）。

## 为什么需要打包？

直接运行 `python script.py` 时存在以下问题：
- Mission Control（调度中心）不显示窗口预览
- Dock 图标显示为 Python 图标而非自定义图标
- 用户需要安装 Python 环境才能运行

打包成 .app 后：
- Mission Control 正确显示窗口预览
- Dock 显示自定义应用图标
- 用户无需安装 Python，双击即可运行

## 准备工作

### 1. 安装 PyInstaller

```bash
pip3 install pyinstaller
```

### 2. 准备应用图标

macOS 应用图标需要 `.icns` 格式。可以从 PNG 图片转换：

```bash
# 创建临时目录存放不同尺寸的图标
mkdir -p AppIcon.iconset

# 生成各种尺寸的图标（假设原图为 icon.png）
sips -z 16 16     icon.png --out AppIcon.iconset/icon_16x16.png
sips -z 32 32     icon.png --out AppIcon.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out AppIcon.iconset/icon_32x32.png
sips -z 64 64     icon.png --out AppIcon.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out AppIcon.iconset/icon_128x128.png
sips -z 256 256   icon.png --out AppIcon.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out AppIcon.iconset/icon_256x256.png
sips -z 512 512   icon.png --out AppIcon.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out AppIcon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out AppIcon.iconset/icon_512x512@2x.png

# 转换为 icns 格式
iconutil -c icns AppIcon.iconset -o AppIcon.icns

# 清理临时目录
rm -rf AppIcon.iconset
```

## 打包命令

### 基本命令

```bash
pyinstaller --onedir --windowed \
  --name "应用名称" \
  --icon "图标路径.icns" \
  --add-data "资源目录:资源目录" \
  --noconfirm \
  主程序.py
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--onedir` | 生成目录形式的应用（推荐，启动更快） |
| `--onefile` | 生成单文件应用（体积更小，但启动稍慢） |
| `--windowed` | 不显示终端窗口（GUI 应用必需） |
| `--name` | 应用名称 |
| `--icon` | 应用图标路径（.icns 格式） |
| `--add-data` | 添加资源文件，格式为 `源路径:目标路径` |
| `--noconfirm` | 覆盖已存在的输出目录 |

### 本项目实际使用的命令

```bash
pyinstaller --onedir --windowed \
  --name "文件搜索工具" \
  --icon "assets/AppIcon.icns" \
  --add-data "assets:assets" \
  --noconfirm \
  FileSearchGUI.py
```

## 输出结果

打包完成后会生成以下目录结构：

```
项目目录/
├── build/              # 构建临时文件（可删除）
├── dist/               # 输出目录
│   ├── 文件搜索工具/     # 应用依赖文件
│   └── 文件搜索工具.app  # macOS 应用包 ← 这是最终产物
├── 文件搜索工具.spec    # PyInstaller 配置文件
└── ...
```

## 使用打包后的应用

1. 进入 `dist` 目录
2. 双击 `文件搜索工具.app` 运行
3. 可将 .app 拖到「应用程序」文件夹或 Dock 中

## 常见问题

### 1. 代码中引用资源文件

打包后资源文件路径会改变，需要使用以下方式获取正确路径：

```python
import sys
import os

def resource_path(relative_path):
    """获取资源文件的绝对路径（兼容打包后的应用）"""
    if hasattr(sys, '_MEIPASS'):
        # 打包后的路径
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # 开发时的路径
        return os.path.join(os.path.dirname(__file__), relative_path)

# 使用示例
icon_path = resource_path("assets/icon.png")
```

### 2. 应用无法打开

如果双击应用显示「已损坏」或「无法验证开发者」：

```bash
# 移除隔离属性
xattr -cr "dist/文件搜索工具.app"
```

### 3. 重新打包

修改代码后重新打包：

```bash
# 方法1：使用 --noconfirm 自动覆盖
pyinstaller --noconfirm 文件搜索工具.spec

# 方法2：先删除旧文件
rm -rf build/ dist/
pyinstaller 文件搜索工具.spec
```

### 4. 减小应用体积

使用 `--exclude-module` 排除不需要的模块：

```bash
pyinstaller --onedir --windowed \
  --exclude-module numpy \
  --exclude-module pandas \
  主程序.py
```

## 其他打包工具

除了 PyInstaller，还可以使用：

- **py2app**：macOS 专用，配置更灵活
- **Nuitka**：编译为原生代码，性能更好
- **briefcase**：跨平台打包工具

## 参考链接

- [PyInstaller 官方文档](https://pyinstaller.org/en/stable/)
- [Apple Human Interface Guidelines - App Icon](https://developer.apple.com/design/human-interface-guidelines/app-icons)
