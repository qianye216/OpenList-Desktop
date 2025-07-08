"""
Author: qianye
Date: 2025-07-05 06:46:15
LastEditTime: 2025-07-08 15:34:23
Description:
"""


# coding: utf-8
from pathlib import Path

from PySide6.QtCore import QStandardPaths

# change DEBUG to False if you want to compile the code to exe
DEBUG = "__compiled__" not in globals()
DEBUG = False


YEAR = 2025
AUTHOR = "qianye"
VERSION = "1.0.1"
APP_NAME = "OpenList Desktop"
HELP_URL = "https://github.com/qianye216/OpenList-Desktop/wiki"
DOC_URL = "https://github.com/qianye216/OpenList-Desktop/wiki"
GITHUB_URL = "https://github.com/qianye216/OpenList-Desktop"
OPENLIST_DOC_RUL = "https://docs.oplist.org/zh/"
OPENLIST_GITHUB_URL = "https://github.com/OpenListTeam/OpenList"
OPENLIST_UPDATE_URL = (
    "https://api.github.com/repos/OpenListTeam/OpenList/releases/latest"
)
RCLONE_DOC_URL = "https://rclone.org/docs/"
RCLONE_GITHUB_URL = "https://github.com/rclone/rclone"
RCLONE_UPDATE_URL = "https://api.github.com/repos/rclone/rclone/releases/latest"
UPDATE_URL = "https://api.github.com/repos/qianye216/OpenList-Desktop/releases/latest"
FEEDBACK_URL = "https://github.com/qianye216/OpenList-Desktop/issues"
SUPPORT_URL = "https://afdian.com/a/qianyei"


CONFIG_FOLDER = (
    Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    )
    / APP_NAME
)
# 确保配置目录存在
CONFIG_FOLDER.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_FOLDER / "config.json"

# 添加OpenList配置文件夹路径定义
OPENLIST_CONFIG_FOLDER = CONFIG_FOLDER / "openlist_config"
# 确保OpenList配置目录存在
OPENLIST_CONFIG_FOLDER.mkdir(parents=True, exist_ok=True)
