# Stellar Search Everything

跨平台文件搜索工具（Qt/PySide6，暗色主题，中英文界面）。

## 运行（Qt 版，推荐）

```shell
pip install -r requirements.txt
python3 FileSearchQt.py
```

## 功能

- 按文件名 / 文件内容搜索，支持多关键词（全部匹配 / 任一匹配）
- 搜索历史、结果排序、右键菜单（打开 / 打开所在文件夹 / 复制路径 / 复制文件）
- 中英文界面切换（状态栏按钮，macOS 另有菜单栏菜单）
- 可调字体大小、紧凑显示，配置自动保存

## 旧版 Tkinter 界面

`FileSearchGUI.py` 为迁移前的 Tkinter 实现，保留作参考：

```shell
python3 FileSearchGUI.py
```

注意：Tkinter 版在部分 Linux 环境（如 conda 自带的无 Xft 的 Tk）下存在字体和性能问题，Qt 版无此问题。

## 发布

推送 `v*` tag 即触发 CI 构建 macOS/Windows/Linux 三平台安装包并创建 GitHub Release，
Release 说明自动取自 `CHANGELOG.md` 中对应版本的小节。
