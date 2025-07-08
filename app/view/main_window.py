"""
Author: qianye
Date: 2025-06-08 20:32:52
LastEditTime: 2025-06-24 17:07:32
Description:
"""

# coding: utf-8
import sys
from PySide6.QtCore import QRect, QSize, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from qfluentwidgets import (
    FluentBackgroundTheme,
    InfoBarIcon,
    MessageBox,
    MSFluentWindow,
    NavigationItemPosition,
    SplashScreen,
    # SystemThemeListener,
    isDarkTheme,
    qconfig,
    setThemeColor,
)
from qfluentwidgets import FluentIcon as FIF

from ..components.loading_dialog import LoadingDialog
from ..components.update_assetdialog import UpdateAssetsDialog

# 导入获取系统主题色的函数
try:
    from qframelesswindow.utils import getSystemAccentColor
except ImportError:

    def getSystemAccentColor():
        """Fallback function for systems where getSystemAccentColor is not available"""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor

        return QColor(Qt.transparent)


from ..common import resource  # noqa: F401
from ..common.concurrent import TaskExecutor
from ..common.config import cfg
from ..common.icon import Icon
from ..common.setting import FEEDBACK_URL, VERSION
from ..common.signal_bus import signalBus
from ..common.utils import get_app_path, killProcess, openUrl
from ..components.markdown_messagebox import MarkDownMessageBox
from ..components.myinfobar import MyInfoBar
from ..components.system_tray_icon import SystemTrayIcon
from ..services.rclone_manager import rcloneManager
from ..services.update_service import UpdateInfo, UpdateTarget, update_service
from .about_interface import AboutInterface
from .home_interface import HomeInterface
from .mount_interface import MountInterface
from .setting_interface import SettingInterface

if sys.platform == "darwin":
    import AppKit

NSApplicationActivationPolicyRegular = 0
NSApplicationActivationPolicyAccessory = 1
NSApplicationActivationPolicyProhibited = 2


class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()

        self.platform = sys.platform

        # 创建主题监听器
        # self.themeListener = SystemThemeListener(self)

        # 在初始化子界面之前先同步系统主题色
        self._syncSystemThemeColor()

        self.initWindow()
        self.initWidget()
        self.initNavigation()
        self.connectSignalToSlot()

        # 初始化全局加载动画
        self.initGlobalLoading()

        if self.platform == "darwin":
            self.setWindowFlags(
                (self.windowFlags() & ~Qt.WindowType.WindowFullscreenButtonHint)
                | Qt.WindowType.CustomizeWindowHint
            )

        self.onInitFinished()

        # 启动监听器
        # self.themeListener.start()

    def initGlobalLoading(self):
        """
        初始化全局加载动画组件
        """

        # 创建全局加载动画实例
        self.globalLoadingDialog = LoadingDialog(
            text="加载中...",
            ring_size=60,
            auto_hide_duration=None,
            parent=self,  # 禁用自动隐藏
        )

        # 确保初始化后默认隐藏
        self.globalLoadingDialog.hide()

    def initWidget(self):
        self.homeInterface = HomeInterface(self)
        self.mountInterface = MountInterface(self)
        self.settingInterface = SettingInterface(self)
        self.aboutInterface = AboutInterface(self)
        self.systemTrayIcon = SystemTrayIcon(self)

    def systemTitleBarRect(self, size: QSize):
        """重写 macOS 三大件到左上角"""
        if sys.platform != "darwin":
            return super().systemTitleBarRect(size)
        return QRect(0, 0 if self.isFullScreen() else 9, 75, size.height())

    def initWindow(self):
        """
        初始化窗口设置，包括窗口大小记忆功能
        """
        # 读取保存的窗口大小配置
        window_size_str = cfg.get(cfg.windowSize)
        try:
            width, height = map(int, window_size_str.split(","))
            
            self.resize(width, height)
        except (ValueError, AttributeError):
            # 如果配置格式错误，使用默认大小
            self.resize(960, 700)

        self.setWindowIcon(QIcon(":/app/images/logo.png"))
        self.setWindowTitle("OpenList-Desktop")

        if self.platform == "darwin":
            self.titleBar.hBoxLayout.insertSpacing(0, 58)

        self.setCustomBackgroundColor(*FluentBackgroundTheme.DEFAULT_BLUE)
        # self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        # create splash screen
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        QApplication.processEvents()

    def connectSignalToSlot(self):
        """连接信号到槽函数"""
        signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)
        signalBus.appMessageSig.connect(self.onAppMessage)
        signalBus.appErrorSig.connect(self.onAppError)
        signalBus.checkUpdateSig.connect(self.checkUpdate)

        self.systemTrayIcon.activated.connect(self.onSystemTrayActivated)
        self.systemTrayIcon.messageClicked.connect(self.showWindow)

        # 修复信号连接语法 - 移除类型参数
        signalBus.success_Signal.connect(self.showMultiSuccessInfo)
        signalBus.success_Signal.connect(self.showSuccessInfo)
        signalBus.warning_Signal.connect(self.showMultiWaringInfo)
        signalBus.warning_Signal.connect(self.showWaringInfo)
        signalBus.error_Signal[str].connect(self.showErrorInfo)
        signalBus.error_Signal[str, str].connect(self.showMultiErrorInfo)

        # 新增：连接加载动画信号
        signalBus.showLoadingSig.connect(self.showGlobalLoading)
        signalBus.hideLoadingSig.connect(self.hideGlobalLoading)
        signalBus.updateLoadingTextSig.connect(self.updateGlobalLoadingText)

    def initNavigation(self):
        # self.navigationInterface.setAcrylicEnabled(True)

        # TODO: add navigation items
        self.addSubInterface(
            self.homeInterface, FIF.HOME, self.tr("主页"), FIF.HOME_FILL
        )

        self.addSubInterface(
            self.mountInterface, FIF.CLOUD_DOWNLOAD, self.tr("挂载"), FIF.CLOUD_DOWNLOAD
        )

        # add custom widget to bottom
        self.addSubInterface(
            self.settingInterface,
            Icon.SETTINGS,
            self.tr("设置"),
            Icon.SETTINGS_FILLED,
            position=NavigationItemPosition.BOTTOM,
        )

        self.addSubInterface(
            self.aboutInterface,
            FIF.INFO,
            self.tr("关于"),
            position=NavigationItemPosition.BOTTOM,
        )

    def onInitFinished(self):
        """应用程序初始化完成后的回调"""

        TaskExecutor.runTask(killProcess).then(
            lambda killed_processes: self._onProcessCleanup(killed_processes)
        )

    def _onProcessCleanup(self, killed_processes):
        """Alist和rclone进程清理完成后的回调"""

        self.splashScreen.finish()
        self.systemTrayIcon.show()

        if cfg.get(cfg.checkUpdateAtStartUp):
            # 延迟5秒后检查更新
            QTimer.singleShot(5000, lambda: self.checkUpdate(True))

    def showWindow(self):
        """一个统一的显示窗口方法"""
        if self.platform == "darwin":
            # 确保在显示窗口前，Dock图标是可见的
            self.showDockIcon()

        # 恢复窗口并激活
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()

        self.raise_()
        self.activateWindow()

    def onSystemTrayActivated(self, reason):
        """
        系统托盘图标被激活时的处理函数。

        参数:
        reason (QSystemTrayIcon.ActivationReason): 激活原因，可能是左键单击、右键单击、双击或中键单击。
        """
        if self.platform == "win32":
            # 在左键单击或双击时，切换窗口可见性
            if (
                reason == QSystemTrayIcon.ActivationReason.Trigger
                or reason == QSystemTrayIcon.ActivationReason.DoubleClick
            ):
                self.showWindow()
            else:
                self.showMinimized()

    def hideDockIcon(self):
        """
        隐藏dock图标
        """
        AppKit.NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)

    def showDockIcon(self):
        """
        恢复dock图标
        """
        AppKit.NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    def onAppMessage(self, message: str):
        if message == "show":
            if self.windowState() & Qt.WindowState.WindowMinimized:
                self.showNormal()

            else:
                if sys.platform == "darwin":
                    self.showDockIcon()
                self.show()
                self.raise_()

        elif message == "hide":
            if self.isMinimized():
                self.showNormal()

            if sys.platform == "darwin":
                hide_dock = cfg.get(cfg.hideDockIcon)  # 新增配置项
                if hide_dock:
                    self.hideDockIcon()
            self.hide()

    def onAppError(self, message: str):
        """app error slot"""
        instance = QApplication.instance()
        if instance is None:
            print(f"Unhandled exception during shutdown: {message}")
            return

        QApplication.clipboard().setText(message)
        self.showMessageBox(
            self.tr("出现未知异常"),
            self.tr("错误日志已写入到剪贴板，是否向作者报告?"),
            True,
            lambda: openUrl(FEEDBACK_URL),
        )

    def showMessageBox(
        self, title: str, content: str, showCancelButton=False, yesSlot=None
    ):
        """show message box"""
        w = MessageBox(title, content, self)
        if not showCancelButton:
            w.yesButton.setText(self.tr("我知道了"))
            w.cancelButton.hide()

        if w.exec() and yesSlot is not None:
            yesSlot()

    def showMarkdownMessageBox(
        self, title: str, content: str, showCancelButton=False, yesSlot=None
    ):
        """show message box"""
        w = MarkDownMessageBox(title, content, self)
        if not showCancelButton:
            w.yesButton.setText(self.tr("我知道了"))
            w.cancelButton.hide()

        if w.exec() and yesSlot is not None:
            yesSlot()

    def checkUpdate(self, ignore=False):
        """检查更新"""
        if not ignore:
            # 显示加载动画
            signalBus.showLoadingSig.emit("正在检查更新...")

        # TaskExecutor 会将 hasNewVersion 的返回值 (字典或None) 传递给 onVersionInfoFetched
        TaskExecutor.runTask(
            lambda: update_service.check_for_updates(UpdateTarget.MAIN_APP, VERSION)
        ).then(lambda updateInfo: self.onVersionInfoFetched(updateInfo, ignore))

    def onVersionInfoFetched(self, updateInfo: UpdateInfo, ignore=False):
        """
        获取到版本信息后的回调函数

        Parameters
        ----------
        updateInfo : dict or None
            如果检测到新版本，它是一个包含 `version` 和 `changelog` 的字典。
            否则为 `None`。
        ignore : bool
            是否是用户手动点击的检查更新（如果是，则在没有更新时也弹出提示）。
        """
        # 隐藏加载动画
        signalBus.hideLoadingSig.emit()

        if updateInfo:
            # 发现新版本，updateInfo 是一个字典
            new_version = updateInfo.version
            changelog = updateInfo.changelog

            w = MarkDownMessageBox(
                self.tr("发现新版本") + f" v{new_version}", changelog, self
            )
            w.yesButton.setText(self.tr("获取更新"))
            if w.exec():
                # 默认安装路径为当前程序的目录
                install_path = get_app_path()
                assets_dialog = UpdateAssetsDialog(updateInfo, install_path, self)
                assets_dialog.exec()

        elif not ignore:
            self.showMessageBox(
                self.tr("暂无新版本"),
                self.tr("已是最新版本，请放心使用"),
            )

    def showMultiSuccessInfo(self, title, content):
        MyInfoBar.success(title, content, parent=self)

    def showSuccessInfo(self, content):
        MyInfoBar.success(title=self.tr("温馨提示"), content=content, parent=self)

    def showMultiWaringInfo(self, title, content):
        MyInfoBar.warning(title, content, parent=self)

    def showWaringInfo(self, content):
        MyInfoBar.warning(title=self.tr("温馨提示"), content=content, parent=self)

    def showMultiErrorInfo(self, title, content):
        MyInfoBar.error(title, content, parent=self)

    def showErrorInfo(self, content):
        MyInfoBar.error(title=self.tr("温馨提示"), content=content, parent=self)

    def _syncSystemThemeColor(self):
        """
        在主窗口初始化时同步系统主题色，确保所有组件使用正确的颜色
        """
        try:
            # 检查是否启用了跟随系统设置
            follow_system = cfg.get(cfg.followSystemThemeColor)

            if follow_system:
                # 获取当前系统主题色
                current_system_color = getSystemAccentColor()
                if current_system_color.isValid():
                    # 获取当前配置中保存的主题色
                    saved_color = qconfig.get(cfg.themeColor)

                    # 如果系统主题色与保存的不同，更新并刷新
                    if saved_color != current_system_color:
                        qconfig.set(cfg.themeColor, current_system_color)
                        # 强制刷新主题色，确保所有组件都收到更新
                        setThemeColor(current_system_color)
                    else:
                        # 即使颜色相同，也要确保主题色被正确应用
                        setThemeColor(current_system_color)

        except Exception:
            # 处理任何可能的异常
            pass

    def _onThemeChangedFinished(self):
        super()._onThemeChangedFinished()

        # 云母特效启用时需要增加重试机制
        if self.isMicaEffectEnabled():
            QTimer.singleShot(
                100,
                lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()),
            )

    def showGlobalLoading(self, text: str = "加载中..."):
        """
        显示全局加载动画

        Args:
            text: 加载提示文案
        """
        if hasattr(self, "globalLoadingDialog"):
            self.globalLoadingDialog.set_text(text)
            self.globalLoadingDialog.show_loading()

    def hideGlobalLoading(self):
        """
        隐藏全局加载动画
        """
        if hasattr(self, "globalLoadingDialog"):
            self.globalLoadingDialog.hide_loading()

    def updateGlobalLoadingText(self, text: str):
        """
        更新全局加载动画文案

        Args:
            text: 新的加载提示文案
        """
        if hasattr(self, "globalLoadingDialog"):
            self.globalLoadingDialog.set_text(text)

    def _saveWindowSize(self):
        """
        保存当前窗口大小到配置文件
        格式: "width,height"
        """
        current_size = self.size()
        size_str = f"{current_size.width()},{current_size.height()}"
        cfg.set(cfg.windowSize, size_str)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "splashScreen"):
            self.splashScreen.resize(self.size())

    def closeEvent(self, event):
        """
        关闭窗口时，保存窗口大小并通知服务进行清理
        """
        # 保存当前窗口大小
        self._saveWindowSize()

        if cfg.get(cfg.trayIcon):
            self.hide()
            event.ignore()

            # 在 Mac 系统下区分关闭方式
            if self.platform == "darwin":
                # event.spontaneous() 为 True 表示来自窗口系统（如点击关闭按钮）
                # event.spontaneous() 为 False 表示程序内部调用（如 dock 右键退出）
                if event.spontaneous():
                    hide_dock = cfg.get(cfg.hideDockIcon)  # 新增配置项
                    if hide_dock:
                        self.hideDockIcon()
                    # 只有点击窗口关闭按钮时才显示托盘消息
                    self.systemTrayIcon.showMessage(
                        "应用仍在运行",
                        "应用已最小化到系统托盘，单击图标可恢复。",
                        InfoBarIcon.INFORMATION.icon(),
                        3000,
                    )

                else:
                    rcloneManager.cleanup() # 清理rclone进程
                    # 停止监听器线程
                    # self.themeListener.terminate()
                    # self.themeListener.deleteLater()
            else:
                # 非 Mac 系统保持原有行为
                self.systemTrayIcon.showMessage(
                    "应用仍在运行",
                    "应用已最小化到系统托盘，单击图标可恢复。",
                    InfoBarIcon.INFORMATION.icon(),
                    3000,
                )
        else:
            self.message_box = MessageBox(
                self.tr("温馨提示"), self.tr("确定要关闭该程序吗？"), self
            )

            if self.message_box.exec():
                # 停止监听器线程
                # self.themeListener.terminate()
                # self.themeListener.deleteLater()
                self.systemTrayIcon.hide()
                rcloneManager.cleanup() # 清理rclone进程
                QApplication.instance().quit()
                event.accept()
            else:
                event.ignore()
