# OpenList Desktop

<p align="center">
  <img src="app/resource/images/logo.png" width="150px" alt="logo"/>
</p>
<h1 align="center">OpenList Desktop</h1>
<p align="center">
  <a href="https://github.com/qianye216/OpenList-Desktop/blob/main/LICENSE" target="_blank">
    <img src="https://img.shields.io/github/license/qianye216/OpenList-Desktop?style=flat-square&color=00a6ed" alt="license">
  </a>
  <a href="https://github.com/qianye216/OpenList-Desktop/releases" target="_blank">
    <img src="https://img.shields.io/github/v/release/qianye216/OpenList-Desktop?style=flat-square&include_prereleases" alt="release">
  </a>
</p>

---

[English](./README.md) | [简体中文](./README.zh-CN.md)

## 📖 简介

**OpenList Desktop** 是一个为 [OpenList (Alist)](https://github.com/OpenListTeam/OpenList) 和 [Rclone](https://rclone.org/) 设计的跨平台桌面客户端。它提供了一个现代化且用户友好的图形界面，帮助您轻松管理 Alist 服务和 Rclone 云盘挂载，无需记忆和输入繁琐的命令行指令。

本项目基于 Python 和 [PySide6](https://www.qt.io/qt-for-python) 构建，并使用了 [QFluentWidgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) 组件库，确保了美观流畅的用户体验。

## ✨ 功能特性

- **Alist 服务管理**: 轻松启动、停止和重启 Alist 服务。
- **Rclone 核心服务**: 管理 Rclone 的核心 `rcd` 服务，为所有挂载操作提供支持。
- **参数化配置**: 为 Alist 和 Rclone 提供图形化的启动参数配置界面。
- **云盘挂载**: 通过 Rclone 的 HTTP API 创建和管理云盘挂载，将云存储映射为本地磁盘。
- **系统集成**: 支持系统托盘，并可在 macOS 上隐藏 Dock 图标，实现真正的后台运行。
- **开机自启**: 可配置应用随系统启动，并支持静默启动。
- **自动更新**: 内置应用本身、Alist 和 Rclone 的更新检查器。
- **个性化主题**: 支持浅色、深色和跟随系统设置的主题，并允许自定义主题色。

## 🖼️ 截图

![Screenshot 1](docs/screenshot/主界面.png)

## 🚀 安装与使用

### 1. 下载应用

从 [GitHub Releases](https://github.com/qianye216/OpenList-Desktop/releases) 页面下载适用于您操作系统的最新版本。

### 2. 准备依赖

#### Rclone 挂载先决条件

为了使用 Rclone 的挂载功能，您需要预先安装以下依赖：

- **Windows**: 安装 [WinFsp](https://winfsp.dev/rel/) (Windows File System Proxy)。
- **macOS**: 安装 [macFUSE](https://osxfuse.github.io/)。
- **Linux**: 通过您的包管理器安装 `fuse`。例如，在 Debian/Ubuntu 上运行 `sudo apt-get install fuse`。

#### Alist & Rclone 可执行文件

将您下载的 `alist` (或 `openlist`) 和 `rclone` 可执行文件放置在您电脑的任意目录中。

### 3. 配置应用

1.  首次运行 **OpenList Desktop**。
2.  导航到 **设置** -> **OpenList设置**。
3.  点击 **工作目录** 旁的 "选择" 按钮，选择您存放 `alist` 可执行文件的文件夹。
4.  导航到 **设置** -> **Rclone设置**。
5.  点击 **工作目录** 旁的 "选择" 按钮，选择您存放 `rclone` 可执行文件的文件夹。
6.  完成配置后，您就可以在主页和挂载页面启动并管理相关服务了。

## 🏗️ 项目结构

```
root
|  main.py                (入口脚本)
|  requirements.txt         (依赖文件)
|
└─app
    ├─common                (通用模块: 配置, 信号总线, 工具函数等)
    ├─components            (自定义UI组件)
    ├─resource              (资源文件: 图标, qss, 国际化文件)
    ├─services              (核心服务: Alist和Rclone管理器)
    └─view                  (界面视图: 主窗口, 各子界面)
```

## 📄 开源许可

本项目基于 [GPL-3.0 License](./LICENSE) 开源。

## 🙏 致谢

- [OpenList (Alist)](https://github.com/OpenListTeam/OpenList): 强大的列表程序。
- [Rclone](https://rclone.org/): The Swiss army knife of cloud storage.
- [QFluentWidgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets): 一个令人惊艳的 Qt 组件库。
- 所有为本项目做出贡献的开发者。