# coding:utf-8
import platform

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtWidgets import QFileDialog, QFrame, QVBoxLayout, QWidget
from qfluentwidgets import (
    ComboBoxSettingCard,
    ExpandLayout,
    OptionsSettingCard,
    PopUpAniStackedWidget,
    PushSettingCard,
    ScrollArea,
    SegmentedWidget,
    SettingCardGroup,
    SwitchSettingCard,
    setTheme,
    setThemeColor,
)
from qfluentwidgets import FluentIcon as FIF

from ..common.auto_startup import add_to_startup, remove_from_startup
from ..common.concurrent import TaskExecutor
from ..common.config import cfg, isWin11
from ..common.signal_bus import signalBus
from ..common.style_sheet import StyleSheet
from ..common.utils import checkAlistExist, checkRcloneExist
from ..components.alist_parameter_dialog import AlistParameterDialog
from ..components.github_proxy_dialog import GitHubProxyDialog
from ..components.github_token_dialog import GitHubTokenDialog
from ..components.markdown_messagebox import MarkDownMessageBox
from ..components.myinfobar import MyInfoBar
from ..components.proxy_setting_card import CustomProxySettingCard
from ..components.rclone_parameter_dialog import RcloneParameterDialog
from ..components.systemcolor_settingcard import SystemColorSettingCard
from ..components.update_assetdialog import UpdateAssetsDialog
from ..components.webdav_account_dialog import WebDavAccountDialog
from ..services.alist_service import alistService
from ..services.rclone_manager import rcloneManager
from ..services.update_service import UpdateTarget, update_service


class PersonalSettingInterface(QWidget):
    """个性化设置页面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._initWidget()
        self._initLayout()
        self._connectSignalToSlot()

    def _initWidget(self):
        self.expandLayout = ExpandLayout(self)
        self.personalGroup = SettingCardGroup(self.tr("个性化"), self)

        self.languageCard = ComboBoxSettingCard(
            cfg.language,
            FIF.LANGUAGE,
            self.tr("语言"),
            self.tr("选择界面所显示的语言"),
            texts=[
                self.tr("简体中文"),
                self.tr("繁體中文"),
                self.tr("English"),
                self.tr("跟随系统设置"),
            ],
            parent=self.personalGroup,
        )

        self.zoomCard = ComboBoxSettingCard(
            cfg.dpiScale,
            FIF.ZOOM,
            self.tr("界面缩放"),
            self.tr("调整应用程序界面的缩放比例"),
            texts=["100%", "125%", "150%", "175%", "200%", self.tr("跟随系统设置")],
            parent=self.personalGroup,
        )

        if isWin11():
            self.micaCard = SwitchSettingCard(
                FIF.TRANSPARENT,
                self.tr("云母效果"),
                self.tr("窗口和表面呈现半透明效果"),
                cfg.micaEnabled,
                self.personalGroup,
            )

        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            self.tr("应用主题"),
            self.tr("调整应用程序的外观"),
            texts=[self.tr("浅色"), self.tr("深色"), self.tr("跟随系统设置")],
            parent=self.personalGroup,
        )
        self.themeColorCard = SystemColorSettingCard(
            cfg.themeColor,
            FIF.PALETTE,
            self.tr("主题色"),
            self.tr("调整应用的主色调"),
            self.personalGroup,
        )

        if platform.system() == "Darwin":
            self.hideDockCard = SwitchSettingCard(
                FIF.APPLICATION,
                self.tr("隐藏Dock图标"),
                self.tr("开启开关后在隐藏应用窗口时将同时隐藏底部程序的Dock图标"),
                configItem=cfg.hideDockIcon,
                parent=self.personalGroup,
            )

    def _initLayout(self):
        self.personalGroup.addSettingCard(self.languageCard)
        self.personalGroup.addSettingCard(self.zoomCard)
        if isWin11():
            self.personalGroup.addSettingCard(self.micaCard)
        self.personalGroup.addSettingCard(self.themeCard)
        self.personalGroup.addSettingCard(self.themeColorCard)

        if platform.system() == "Darwin":
            self.personalGroup.addSettingCard(self.hideDockCard)

        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(0, 0, 0, 0)
        self.expandLayout.addWidget(self.personalGroup)

    def _connectSignalToSlot(self):
        cfg.themeChanged.connect(setTheme)
        if isWin11():
            self.micaCard.checkedChanged.connect(signalBus.micaEnableChanged)
        cfg.appRestartSig.connect(self.__showRestartTooltip)
        self.themeColorCard.colorChanged.connect(setThemeColor)

    def __showRestartTooltip(self):
        """show restart tooltip"""
        MyInfoBar.success(
            self.tr("设置成功"),
            self.tr("配置将在重启软件后生效"),
            duration=1500,
            parent=self.window(),
        )


class BasicSettingInterface(QWidget):
    """基本设置界面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._initWidget()
        self._initLayout()
        self._connectSignalToSlot()
        self._load_settings()

    def _initWidget(self):
        self.expandLayout = ExpandLayout(self)
        self.basicSettingGroup = SettingCardGroup(self.tr("基本设置"), self)

        self.trayIconCard = SwitchSettingCard(
            FIF.COMMAND_PROMPT,
            self.tr("最小化到系统托盘"),
            self.tr("开启开关后在关闭程序时最小化到系统托盘"),
            configItem=cfg.trayIcon,
            parent=self.basicSettingGroup,
        )

        self.autoStartupCard = SwitchSettingCard(
            FIF.ROBOT,
            self.tr("开机自启"),
            self.tr("开启开关后在开机后自动启动主程序"),
            configItem=cfg.mainAutoStartUp,
            parent=self.basicSettingGroup,
        )

        self.quietAutoStartCard = SwitchSettingCard(
            FIF.VPN,
            self.tr("静默启动"),
            self.tr("开启开关后静默启动主程序"),
            configItem=cfg.quietAutoStartUp,
            parent=self.basicSettingGroup,
        )

        # 软件启动是检查更新
        self.checkUpdateAtStartUpCard = SwitchSettingCard(
            FIF.UPDATE,
            self.tr("启动时检查更新"),
            self.tr("开启开关后启动时检查版本更新，新版本将更稳定，并带有更多功能"),
            configItem=cfg.checkUpdateAtStartUp,
            parent=self.basicSettingGroup,
        )

        self.proxySettingCard = CustomProxySettingCard(
            cfg.proxyServer,
            parent=self.basicSettingGroup,
        )

        # GitHub令牌设置卡片
        self.githubTokenCard = PushSettingCard(
            self.tr("设置"),
            FIF.GITHUB,
            self.tr("GitHub 访问令牌"),
            self.tr("设置GitHub访问令牌以避免API频率限制"),
            parent=self.basicSettingGroup,
        )

        # GitHub代理设置卡片
        self.githubProxyCard = PushSettingCard(
            self.tr("设置代理"),
            FIF.GLOBE,
            self.tr("GitHub 代理"),
            self.tr("为GitHub相关下载设置代理以加速"),
            parent=self.basicSettingGroup,
        )

    def _initLayout(self):
        self.basicSettingGroup.addSettingCard(self.trayIconCard)
        self.basicSettingGroup.addSettingCard(self.autoStartupCard)
        self.basicSettingGroup.addSettingCard(self.quietAutoStartCard)
        self.basicSettingGroup.addSettingCard(self.checkUpdateAtStartUpCard)
        self.basicSettingGroup.addSettingCard(self.proxySettingCard)
        self.basicSettingGroup.addSettingCard(self.githubTokenCard)
        self.basicSettingGroup.addSettingCard(self.githubProxyCard)

        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(0, 0, 0, 0)
        self.expandLayout.addWidget(self.basicSettingGroup)

    def _connectSignalToSlot(self):
        # 开机启动
        self.autoStartupCard.checkedChanged.connect(self._onAutoStartupCardClicked)
        # GitHub令牌设置
        self.githubTokenCard.clicked.connect(self._setGithubToken)
        # GitHub代理设置
        self.githubProxyCard.clicked.connect(self._setGithubProxy)
        cfg.githubProxy.valueChanged.connect(self._updateGithubProxyDisplay)

    def _load_settings(self):
        """加载初始设置并更新UI"""
        self._updateGithubProxyDisplay(cfg.get(cfg.githubProxy))

    def _updateGithubProxyDisplay(self, proxy: str):
        """更新GitHub代理卡片的显示内容"""
        if proxy:
            self.githubProxyCard.setContent(
                self.tr("已设置GitHub代理：{}").format(proxy)
            )
        else:
            self.githubProxyCard.setContent(self.tr("为GitHub相关下载设置代理以加速"))

    def _onAutoStartupCardClicked(self, checked):
        """处理开机自启动设置"""
        try:
            if checked:
                add_to_startup()

                MyInfoBar.success(
                    title=self.tr("温馨提示"),
                    content=self.tr("设置开机自启成功!"),
                    parent=self.window(),
                )

            else:
                remove_from_startup()
                MyInfoBar.success(
                    title=self.tr("温馨提示"),
                    content=self.tr("取消开机自启成功!"),
                    parent=self.window(),
                )

        except Exception as e:
            signalBus.warning_Signal.emit(self.tr("设置开机自启失败：") + str(e))

    def _setGithubToken(self):
        """
        设置GitHub令牌
        """
        current_token = cfg.get(cfg.githubToken)

        # 创建自定义对话框
        dialog = GitHubTokenDialog(current_token, self.window())

        # 显示对话框并获取结果
        if dialog.exec():
            token = dialog.getToken()
            cfg.set(cfg.githubToken, token)

            if token:
                MyInfoBar.success(
                    self.tr("设置成功"),
                    self.tr("GitHub访问令牌已设置"),
                    duration=2000,
                    parent=self.window(),
                )
            else:
                MyInfoBar.info(
                    self.tr("令牌已清除"),
                    self.tr("GitHub访问令牌已清除"),
                    duration=2000,
                    parent=self.window(),
                )

    def _setGithubProxy(self):
        """
        设置GitHub代理
        """
        current_proxy = cfg.get(cfg.githubProxy)

        # 创建自定义对话框
        dialog = GitHubProxyDialog(current_proxy, self.window())

        # 显示对话框并获取结果
        if dialog.exec():
            proxy = dialog.getProxy()
            cfg.set(cfg.githubProxy, proxy)

            if proxy:
                MyInfoBar.success(
                    self.tr("设置成功"),
                    self.tr("GitHub代理已设置"),
                    duration=2000,
                    parent=self.window(),
                )
            else:
                MyInfoBar.info(
                    self.tr("代理已清除"),
                    self.tr("GitHub代理已清除"),
                    duration=2000,
                    parent=self.window(),
                )


class AlistSettingInterface(QWidget):
    """Alist设置界面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.alist_current_version = alistService.getVersionNumber()
        self._initWidget()
        self._initLayout()
        self._connectSignalToSlot()

    def _initWidget(self):
        """初始化组件"""
        self.expandLayout = ExpandLayout(self)
        self.alistSettingGroup = SettingCardGroup(self.tr("OpenList设置"), self)

        # Alist自动启动开关
        self.alistAutoStartupCard = SwitchSettingCard(
            FIF.ROBOT,
            self.tr("允许 OpenList 自动启动"),
            self.tr("这将在 OpenList Desktop  启动时自动启动 OpenList。"),
            configItem=cfg.alistAutoStartUp,
            parent=self.alistSettingGroup,
        )

        # 工作目录设置
        self.workDirectoryCard = PushSettingCard(
            self.tr("选择"),
            FIF.FOLDER,
            self.tr("工作目录"),
            cfg.alistWorkDirectory.value or self.tr("未设置工作目录"),
            parent=self.alistSettingGroup,
        )

        # 启动参数列表
        self.startupParamsCard = PushSettingCard(
            self.tr("编辑"),
            FIF.COMMAND_PROMPT,
            self.tr("自定义启动参数"),
            f"启动参数： {' '.join(cfg.alistStartupParams.value)}"
            if cfg.alistStartupParams.value
            else "未设置启动参数",
            parent=self.alistSettingGroup,
        )

        # 检查更新卡片
        self.checkUpdateCard = PushSettingCard(
            self.tr("检查更新"),
            FIF.UPDATE,
            self.tr("OpenList 版本更新"),
            self.tr("检查 OpenList 是否有新版本可用，当前版本：v{}").format(
                self.alist_current_version
            ),
            parent=self.alistSettingGroup,
        )

    def _initLayout(self):
        """初始化布局"""
        self.alistSettingGroup.addSettingCard(self.alistAutoStartupCard)
        self.alistSettingGroup.addSettingCard(self.workDirectoryCard)
        self.alistSettingGroup.addSettingCard(self.startupParamsCard)
        self.alistSettingGroup.addSettingCard(self.checkUpdateCard)

        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(0, 0, 0, 0)
        self.expandLayout.addWidget(self.alistSettingGroup)

    def _connectSignalToSlot(self):
        """连接信号与槽"""
        self.workDirectoryCard.clicked.connect(self._selectWorkDirectory)
        self.startupParamsCard.clicked.connect(self._editStartupParams)
        self.checkUpdateCard.clicked.connect(self._checkAlistUpdate)
        cfg.alistWorkDirectory.valueChanged.connect(self._updateWorkDirectoryDisplay)

    def _selectWorkDirectory(self):
        """选择工作目录"""

        directory = QFileDialog.getExistingDirectory(
            self,
            self.tr("选择工作目录"),
            cfg.alistWorkDirectory.value
            or QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.HomeLocation
            ),
        )

        if directory:
            # 判断该目录下是否有openlist或者alist程序
            if checkAlistExist(directory):
                cfg.set(cfg.alistWorkDirectory, directory)
                signalBus.success_Signal.emit(self.tr("OpenList工作目录设置成功！"))
                return

            signalBus.warning_Signal.emit(self.tr("该文件夹下未发下OpenList主程序！"))

    def _editStartupParams(self):
        """编辑启动参数"""
        # 这里可以实现一个对话框来编辑启动参数
        current_params = cfg.get(cfg.alistStartupParams)
        params_dialog = AlistParameterDialog(current_params, self.window())
        if params_dialog.exec():
            selected_params = params_dialog.getSelectedParameters()
            cfg.set(cfg.alistStartupParams, selected_params)
            if not selected_params:
                self.startupParamsCard.setContent("未设置启动参数")
                return
            parsed_params = " ".join(selected_params)
            self.startupParamsCard.setContent(f"启动参数: {parsed_params}")

    def _updateWorkDirectoryDisplay(self):
        """更新工作目录显示"""
        directory = cfg.alistWorkDirectory.value
        display_text = directory if directory else self.tr("未设置工作目录")
        self.workDirectoryCard.setContent(display_text)

    def _checkAlistUpdate(self):
        """检查OpenList更新"""
        signalBus.showLoadingSig.emit(self.tr("检查更新中..."))
        current_version = alistService.getVersionNumber()
        # 使用TaskExecutor异步检查更新
        TaskExecutor.runTask(
            lambda: update_service.check_for_updates(
                UpdateTarget.ALIST, current_version
            )
        ).then(self._onAlistUpdateChecked)

    def _onAlistUpdateChecked(self, updateInfo):
        """
        OpenList更新检查完成后的回调函数

        Parameters
        ----------
        updateInfo : UpdateInfo or None
            如果检测到新版本，它是一个包含版本信息和资源列表的对象。
            否则为 None。
        """
        # 隐藏加载动画并恢复按钮状态
        signalBus.hideLoadingSig.emit()

        if updateInfo:
            # 发现新版本，显示更新对话框
            title = self.tr("发现 OpenList 新版本") + f" v{updateInfo.version}"

            # 创建Markdown内容
            content = updateInfo.changelog
            dialog = MarkDownMessageBox(title, content, self.window())
            dialog.yesButton.setText(self.tr("获取更新"))

            if dialog.exec():
                # 用户点击了"获取更新"，显示资源下载对话框
                install_path = cfg.get(
                    cfg.alistWorkDirectory
                ) or QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.DownloadLocation
                )
                assets_dialog = UpdateAssetsDialog(
                    updateInfo, install_path, self.window()
                )
                assets_dialog.exec()
        else:
            signalBus.success_Signal.emit(self.tr("当前已是最新版本！"))


class RcloneSettingInterface(QWidget):
    """Rclone设置界面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # 安全地获取版本号，避免在工作目录未配置时阻塞UI初始化
        try:
            self.rclone_current_version = rcloneManager.get_rclone_version_number()
        except Exception:
            self.rclone_current_version = "未配置"

        self._initWidget()
        self._initLayout()
        self._connectSignalToSlot()
        self._load_settings()  # 初始化时加载设置

    def _initWidget(self):
        """初始化组件"""
        self.expandLayout = ExpandLayout(self)
        self.rcloneSettingGroup = SettingCardGroup(self.tr("Rclone设置"), self)

        self.startAfterAlistCard = SwitchSettingCard(
            FIF.ROBOT,
            self.tr("在 OpenList 启动后启动"),
            self.tr("这将在 OpenList 服务启动成功后才启动 Rclone 服务。"),
            configItem=cfg.rcloneStartAfterAlist,
            parent=self.rcloneSettingGroup,
        )

        self.workDirectoryCard = PushSettingCard(
            self.tr("选择"),
            FIF.FOLDER,
            self.tr("工作目录"),
            cfg.rcloneWorkDirectory.value or self.tr("未设置工作目录"),
            parent=self.rcloneSettingGroup,
        )

        self.startupParamsCard = PushSettingCard(
            self.tr("编辑"),
            FIF.COMMAND_PROMPT,
            self.tr("启动参数列表"),
            self.tr("点击编辑启动参数"),
            parent=self.rcloneSettingGroup,
        )

        self.webDavAccountCard = PushSettingCard(
            self.tr("编辑"),
            FIF.PEOPLE,
            self.tr("WebDav 账户"),
            self.tr("配置用于挂载的 WebDav 账户"),
            parent=self.rcloneSettingGroup,
        )

        # 检查更新卡片
        self.checkUpdateCard = PushSettingCard(
            self.tr("检查更新"),
            FIF.UPDATE,
            self.tr("Rclone 版本更新"),
            self.tr("检查 Rclone 是否有新版本可用，当前版本：v{}").format(
                self.rclone_current_version
            ),
            parent=self.rcloneSettingGroup,
        )

    def _initLayout(self):
        """初始化布局"""
        self.rcloneSettingGroup.addSettingCard(self.startAfterAlistCard)
        self.rcloneSettingGroup.addSettingCard(self.workDirectoryCard)
        self.rcloneSettingGroup.addSettingCard(self.startupParamsCard)
        self.rcloneSettingGroup.addSettingCard(self.webDavAccountCard)
        self.rcloneSettingGroup.addSettingCard(self.checkUpdateCard)
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(0, 0, 0, 0)
        self.expandLayout.addWidget(self.rcloneSettingGroup)

    def _connectSignalToSlot(self):
        """连接信号与槽"""
        self.workDirectoryCard.clicked.connect(self._selectWorkDirectory)
        self.startupParamsCard.clicked.connect(self._editStartupParams)
        self.webDavAccountCard.clicked.connect(self._editWebDavAccount)
        self.checkUpdateCard.clicked.connect(self._checkRcloneUpdate)
        cfg.rcloneWorkDirectory.valueChanged.connect(self._updateWorkDirectoryDisplay)
        cfg.rcloneStartupParams.valueChanged.connect(self._updateStartupParamsDisplay)
        cfg.rcloneWebDavAccount.valueChanged.connect(self._updateWebDavAccountDisplay)

    def _load_settings(self):
        """加载并显示当前设置"""
        self._updateWorkDirectoryDisplay()
        self._updateStartupParamsDisplay()
        self._updateWebDavAccountDisplay()

    def _selectWorkDirectory(self):
        """选择工作目录"""
        directory = QFileDialog.getExistingDirectory(
            self,
            self.tr("选择工作目录"),
            cfg.rcloneWorkDirectory.value
            or QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.HomeLocation
            ),
        )
        if directory and checkRcloneExist(directory):
            cfg.set(cfg.rcloneWorkDirectory, directory)
            signalBus.success_Signal.emit(self.tr("Rclone工作目录设置成功！"))
        elif directory:
            signalBus.warning_Signal.emit(self.tr("该文件夹下未发现Rclone主程序！"))

    def _editStartupParams(self):
        """编辑启动参数"""

        current_params = cfg.get(cfg.rcloneStartupParams) or []

        params_dialog = RcloneParameterDialog(current_params, self.window())
        if params_dialog.exec():
            selected_params = params_dialog.getSelectedParameters()
            print("rclone启动选择的参数:", selected_params)
            cfg.set(cfg.rcloneStartupParams, selected_params)
            signalBus.success_Signal.emit(self.tr("Rclone启动参数已更新。"))

    def _editWebDavAccount(self):
        """编辑WebDav账户"""

        current_config = cfg.get(cfg.rcloneWebDavAccount)
        dialog = WebDavAccountDialog(current_config, self.window())

        if dialog.exec():
            new_config = dialog.get_config()
            cfg.set(cfg.rcloneWebDavAccount, new_config)
            signalBus.success_Signal.emit(self.tr("WebDav账户已更新。"))

    def _updateWorkDirectoryDisplay(self, directory=None):
        """更新工作目录显示"""
        directory = directory or cfg.rcloneWorkDirectory.value
        self.workDirectoryCard.setContent(directory or self.tr("未设置工作目录"))

    def _updateStartupParamsDisplay(self, params=None):
        """更新启动参数显示"""
        params = params or cfg.rcloneStartupParams.value
        self.startupParamsCard.setContent(
            " ".join(params) if params else self.tr("未设置启动参数")
        )

    def _updateWebDavAccountDisplay(self, account=None):
        """更新WebDav账户显示"""
        pass
        # user, _ = cfg.get_webdav_credentials()
        # self.webDavAccountCard.setContent(self.tr("当前用户: ") + user if user else self.tr("未配置"))

    def _checkRcloneUpdate(self):
        """检查Rclone更新"""
        signalBus.showLoadingSig.emit(self.tr("检查更新中..."))

        current_version = rcloneManager.get_rclone_version_number()
        # 使用TaskExecutor异步检查更新
        TaskExecutor.runTask(
            lambda: update_service.check_for_updates(
                UpdateTarget.RCLONE, current_version
            )
        ).then(self._onRcloneUpdateChecked)

    def _onRcloneUpdateChecked(self, updateInfo):
        """
        Rclone更新检查完成后的回调函数

        Parameters
        ----------
        updateInfo : UpdateInfo or None
            如果检测到新版本，它是一个包含版本信息和资源列表的对象。
            否则为 None。
        """
        # 隐藏加载动画并恢复按钮状态
        signalBus.hideLoadingSig.emit()

        if updateInfo:
            # 发现新版本，显示更新对话框
            title = self.tr("发现 Rclone 新版本") + f" v{updateInfo.version}"

            # 创建Markdown内容
            content = updateInfo.changelog

            dialog = MarkDownMessageBox(title, content, self.window())
            dialog.yesButton.setText(self.tr("获取更新"))

            if dialog.exec():
                # 用户点击了"获取更新"，显示资源下载对话框
                install_path = cfg.get(
                    cfg.rcloneWorkDirectory
                ) or QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.DownloadLocation
                )
                assets_dialog = UpdateAssetsDialog(
                    updateInfo, install_path, self.window()
                )
                assets_dialog.exec()
        else:
            signalBus.success_Signal.emit("当前已是最新版本！")

    def _updateStartupParamsDisplay(self, params=None):
        """更新启动参数显示"""
        params = params or cfg.rcloneStartupParams.value
        self.startupParamsCard.setContent(
            " ".join(params) if params else self.tr("未设置启动参数")
        )

    def _updateWebDavAccountDisplay(self, account=None):
        """更新WebDav账户显示"""
        pass
        # user, _ = cfg.get_webdav_credentials()
        # self.webDavAccountCard.setContent(self.tr("当前用户: ") + user if user else self.tr("未配置"))


class SettingInterface(QWidget):
    """Setting interface"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._initWidget()
        self._initLayout()
        self._connectSignalToSlot()

    def _initWidget(self):
        self.setObjectName("SettingInterface")
        StyleSheet.SETTING_INTERFACE.apply(self)

        self.pivot = SegmentedWidget(self)
        self.scrollArea = ScrollArea(self)
        self.stackedWidget = PopUpAniStackedWidget()

        self.personalSettingInterface = PersonalSettingInterface()
        self.basicSettingInterface = BasicSettingInterface()
        self.alistSettingInterface = AlistSettingInterface()
        self.rcloneSettingInterface = RcloneSettingInterface()

    def _initLayout(self):
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 10, 16, 10)
        self.vBoxLayout.setSpacing(10)

        self.vBoxLayout.addWidget(self.pivot)
        self.vBoxLayout.addWidget(self.scrollArea)

        self.scrollArea.setWidget(self.stackedWidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scrollArea.enableTransparentBackground()
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)

        self.addSubInterface(
            self.personalSettingInterface, "PersonalSettingInterface", self.tr("个性化")
        )
        self.addSubInterface(
            self.basicSettingInterface, "BasicSettingInterface", self.tr("基本设置")
        )
        self.addSubInterface(
            self.alistSettingInterface, "AlistSettingInterface", self.tr("OpenList设置")
        )
        self.addSubInterface(
            self.rcloneSettingInterface, "RcloneSettingInterface", self.tr("Rclone设置")
        )

        self.stackedWidget.setCurrentWidget(self.personalSettingInterface)
        self.pivot.setCurrentItem(self.personalSettingInterface.objectName())

    def _connectSignalToSlot(self):
        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)

    def addSubInterface(self, widget: QWidget, objectName, text):
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget),
        )

    def switchTo(self, index):
        self.stackedWidget.setCurrentIndex(index)
        widget = self.stackedWidget.widget(index)
        self.pivot.setCurrentItem(widget.objectName())

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.pivot.setCurrentItem(widget.objectName())
