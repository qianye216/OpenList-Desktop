"""
Author: qianye
Date: 2025-06-08 20:32:52
LastEditTime: 2025-06-27 16:47:20
Description:
"""

# coding:utf-8
import json
import re
import sys
from enum import Enum

from PySide6.QtCore import QLocale
from qfluentwidgets import (
    BoolValidator,
    ConfigItem,
    ConfigSerializer,
    ConfigValidator,
    OptionsConfigItem,
    OptionsValidator,
    QConfig,
    qconfig,
)

from .setting import CONFIG_FILE, OPENLIST_CONFIG_FOLDER
from .utils import get_app_path


class Language(Enum):
    """Language enumeration"""

    CHINESE_SIMPLIFIED = QLocale(QLocale.Language.Chinese, QLocale.Country.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Language.Chinese, QLocale.Country.HongKong)
    ENGLISH = QLocale(QLocale.Language.English)
    AUTO = QLocale()


class ProxyValidator(ConfigValidator):
    PATTERN = re.compile(
        r"^(socks5|http|https):\/\/"
        r"((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):"
        r"(6553[0-5]|655[0-2][0-9]|65[0-4][0-9]{2}|[1-5]?[0-9]{1,4})$"
    )

    def validate(self, value: str) -> bool:
        return bool(self.PATTERN.match(value)) or value == "Auto" or value == "Off"

    def correct(self, value) -> str:
        return value if self.validate(value) else "Auto"


class LanguageSerializer(ConfigSerializer):
    """Language serializer"""

    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO


class MountListSerializer(ConfigSerializer):

    def serialize(self, value: list) -> str:
        if not isinstance(value, list):
            return "[]"
        return json.dumps(value, ensure_ascii=False)

    def deserialize(self, value: str) -> list:
        try:
            data = json.loads(value)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []


class WebDavAccountSerializer(ConfigSerializer):
    def serialize(self, value: dict) -> str:
        if not isinstance(value, dict):
            return "{}"
        return json.dumps(value, ensure_ascii=False)

    def deserialize(self, value: str) -> dict:
        try:
            data = json.loads(value)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}


class ListValidator(ConfigValidator):
    """Validator for list type"""

    def validate(self, value) -> bool:
        return isinstance(value, list)

    def correct(self, value):
        return value if self.validate(value) else []


class WindowSizeValidator(ConfigValidator):
    """窗口大小校验器，验证格式为 'width,height'"""
    
    def validate(self, value: str) -> bool:
        """
        验证窗口大小格式是否正确
        
        Args:
            value: 窗口大小字符串，格式为 'width,height'
            
        Returns:
            bool: 验证是否通过
        """
        if not isinstance(value, str):
            return False
            
        try:
            parts = value.split(',')
            if len(parts) != 2:
                return False
                
            width, height = map(int, parts)
            
            # 验证窗口大小是否在合理范围内
            # 最小宽度760，最小高度500，最大不超过屏幕分辨率的合理范围
            if width < 760 or height < 500:
                return False
            if width > 3840 or height > 2160:  # 4K分辨率作为上限
                return False
                
            return True
        except (ValueError, AttributeError):
            return False
    
    def correct(self, value) -> str:
        """
        修正不合法的窗口大小值
        
        Args:
            value: 原始值
            
        Returns:
            str: 修正后的窗口大小字符串
        """
        if self.validate(value):
            return value
        else:
            # 返回默认窗口大小
            return "960,700"


def isWin11():
    return sys.platform == "win32" and sys.getwindowsversion().build >= 22000


class Config(QConfig):
    """Config of application"""

    # 个性化设置
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", False, BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow",
        "DpiScale",
        "Auto",
        OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]),
        restart=True,
    )
    language = OptionsConfigItem(
        "MainWindow",
        "Language",
        Language.CHINESE_SIMPLIFIED,
        OptionsValidator(Language),
        LanguageSerializer(),
        restart=True,
    )

    hideDockIcon = ConfigItem("MainWindow", "hideDockIcon", True, BoolValidator())
    
    # 主题色跟随系统设置
    followSystemThemeColor = ConfigItem("MainWindow", "followSystemThemeColor", True, BoolValidator())
    
    # 窗口大小记忆功能 - 格式: "width,height"
    windowSize = ConfigItem("MainWindow", "windowSize", "960,700", WindowSizeValidator())

    proxyServer = ConfigItem("MainWindow", "proxyServer", "Auto", ProxyValidator())

    # 基本设置页面
    trayIcon = ConfigItem("StartUp", "trayIcon", True, BoolValidator())
    mainAutoStartUp = ConfigItem("StartUp", "mainAutoStartUp", False, BoolValidator())
    quietAutoStartUp = ConfigItem("StartUp", "quietAutoStartUp", False, BoolValidator())
    checkUpdateAtStartUp = ConfigItem(
        "StartUp", "CheckUpdateAtStartUp", True, BoolValidator()
    )
    # GitHub令牌设置
    githubToken = ConfigItem("StartUp", "githubToken", "")
    # GitHub代理设置
    githubProxy = ConfigItem("StartUp", "githubProxy", "")

    # Alist设置
    alistAutoStartUp = ConfigItem("Alist", "alistAutoStartUp", False, BoolValidator())
    alistWorkDirectory = ConfigItem("Alist", "workDirectory", str(get_app_path() / "tools"))
    alistHttpProxy = ConfigItem("Alist", "httpProxy", "")
    alistStartupParams = ConfigItem("Alist", "startupParams", ["--data", str(OPENLIST_CONFIG_FOLDER)])

    # Rclone设置
    rcloneAutoStartUp = ConfigItem(
        "Rclone", "rcloneAutoStartUp", False, BoolValidator()
    )
    rcloneStartAfterAlist = ConfigItem(
        "Rclone", "startAfterAlist", False, BoolValidator()
    )
    rcloneWorkDirectory = ConfigItem("Rclone", "workDirectory", str(get_app_path() / "tools"))
    rcloneStartupParams = ConfigItem(
        "Rclone",
        "startupParams",
        [
            "rcd",
            "--rc-user",
            "admin",
            "--rc-pass",
            "admin",
            "--rc-web-gui-no-open-browser",
        ],
    )
    rcloneWebDavAccount = ConfigItem(
        "Rclone", "webDavAccount", {}, serializer=WebDavAccountSerializer()
    )

    mountConfigs = ConfigItem(
        "Rclone", "mountConfigs", [], ListValidator(), serializer=MountListSerializer()
    )

    # 添加首次提示配置项
    firstMountTipShown = ConfigItem("MainWindow", "firstMountTipShown", False, BoolValidator())

cfg = Config()
print(str(CONFIG_FILE.absolute()))
qconfig.load(str(CONFIG_FILE.absolute()), cfg)
