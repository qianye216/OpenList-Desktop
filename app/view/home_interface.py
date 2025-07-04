import platform

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
    InfoBadge,
    InfoBadgePosition,
    LargeTitleLabel,
    MessageBox,
    PrimaryDropDownPushButton,
    PrimaryPushButton,
    RoundMenu,
    TextEdit,
    setFont,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from ..common.config import cfg
from ..common.signal_bus import signalBus
from ..components.admininfo_dialog import AdminInfoDialog
from ..components.link_buttons_card import LinkButtonsCard

# 关键：导入服务单例
from ..services.alist_service import alistService

# 在文件顶部的导入部分添加rcloneManager导入
from ..services.rclone_manager import rcloneManager


class HomeInterface(QWidget):
    """主页界面类，作为 Alist 服务的视图"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("HomeInterface")

        self.alist_url: str | None = None
        self.alist_info_badge: InfoBadge | None = None
        self.platform_name = platform.system()

        self._initWidget()
        self._initLayout()
        self._connectSignalToSlot()

        # 如果开启了自动启动，则通知服务启动
        if cfg.alistAutoStartUp.value:
            QTimer.singleShot(500, alistService.start)

    def _initWidget(self):
        """初始化组件"""
        self.vboxLayout = QVBoxLayout(self)

        # 大标题
        self.AlistTitleLabel = LargeTitleLabel("OpenList Desktop", self)
        self.AlistTitleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 控制按钮
        self.start_button = PrimaryPushButton(self.tr("启动"), self)
        self.start_button.setIcon(FIF.PLAY)

        self.restart_button = PrimaryPushButton(self.tr("重启"), self)
        self.restart_button.setIcon(FIF.SYNC)

        self.password_button = PrimaryPushButton(self.tr("查看密码"), self)
        self.password_button.setIcon(FIF.VIEW)

        # 更多按钮（下拉菜单）
        self.more_button = PrimaryDropDownPushButton(self.tr("更多"), self)
        self.more_button.setIcon(FIF.MORE)

        # 创建更多菜单
        self._initMoreMenu()

        # 日志显示区域
        self.log_text_edit = TextEdit(self)
        self.log_text_edit.setPlaceholderText(
            self.tr("Alist 运行日志将在这里显示...\n您可以随时在'更多'菜单中清除日志！")
        )
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setMinimumHeight(200)

        # 使用新的链接按钮卡片组件
        self.link_buttons_card = LinkButtonsCard(self)

    def _initMoreMenu(self):
        """初始化更多菜单"""
        menu = RoundMenu(parent=self)

        menu.addAction(
            Action(FIF.GLOBE, self.tr("在浏览器中打开"), triggered=self.open_in_browser)
        )
        menu.addSeparator()
        menu.addAction(
            Action(FIF.FLAG, self.tr("查看版本"), triggered=alistService.getVersion)
        )
        menu.addAction(
            Action(
                FIF.DOCUMENT, self.tr("打开配置文件"), triggered=alistService.open_config_file
            )
        )
        menu.addAction(
            Action(FIF.FOLDER, self.tr("打开日志文件夹"), triggered=alistService.open_log_dir)
        )
        menu.addAction(
            Action(FIF.CLOUD, self.tr("查看WebDAV地址"), triggered=self.show_webdav_url)
        )
        menu.addAction(
            Action(
                FIF.TRANSPARENT,
                self.tr("取消双重验证"),
                triggered=alistService.disable2FA,
            )
        )
        menu.addSeparator()
        menu.addAction(
            Action(
                FIF.BROOM,
                self.tr("清空日志"),
                triggered=lambda: self.log_text_edit.clear(),
            )
        )

        self.more_button.setMenu(menu)

    def _initLayout(self):
        """初始化布局"""
        title_layout = QHBoxLayout()
        title_layout.addStretch()
        title_layout.addWidget(self.AlistTitleLabel)
        title_layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.restart_button)
        button_layout.addWidget(self.password_button)
        button_layout.addWidget(self.more_button)

        self.vboxLayout.setSpacing(20)
        self.vboxLayout.setContentsMargins(16, 20, 16, 20)
        self.vboxLayout.addLayout(title_layout)
        self.vboxLayout.addLayout(button_layout)
        self.vboxLayout.addWidget(self.log_text_edit)
        self.vboxLayout.addWidget(self.link_buttons_card)

    def _connectSignalToSlot(self):
        """连接UI事件到服务调用，以及服务信号到UI更新"""

        self.start_button.clicked.connect(self.toggle_alist_service)
        self.restart_button.clicked.connect(alistService.restart)
        self.password_button.clicked.connect(self.show_password_dialog)

        alistService.stateChanged.connect(self.on_alist_state_changed)
        alistService.logMessageReady.connect(self.append_log)
        alistService.passwordReady.connect(self.on_password_ready)
        alistService.versionReady.connect(self.on_version_ready)
        alistService.twoFactorAuthDisabled.connect(
            lambda: signalBus.success_Signal.emit(self.tr("双重验证已成功禁用！"))
        )
        alistService.configurationRequired.connect(self.handle_configuration_required)
        alistService.errorOccurred.connect(self.on_service_error)
        alistService.operationFailed.connect(signalBus.warning_Signal.emit)
        cfg.alistStartupParams.valueChanged.connect(self.on_alist_startup_params_changed)
        
        

    def toggle_alist_service(self):
        """根据服务当前状态，启动或停止服务"""
        if alistService.is_running:
            alistService.stop()
        else:
            alistService.start()

    def show_password_dialog(self):
        """显示密码对话框，并根据结果调用服务"""
        dialog = AdminInfoDialog(self.window())
        if dialog.exec():
            password = dialog.getPassword()
            if password:
                alistService.setPassword(password)
            else:
                alistService.getRandomPassword()

    def handle_configuration_required(self):
        """
        处理配置请求，显示配置对话框并导航到设置页面
        """
        message_box = MessageBox(
            "温馨提示", 
            "请先配置好Alist的工作目录", 
            self.window()
        )
        if message_box.exec():
            self.window().switchTo(self.window().settingInterface)
            self.window().settingInterface.switchTo(2)

    

    def open_in_browser(self):
        """在浏览器中打开Alist页面"""
        if not alistService.is_running or not self.alist_url:
            signalBus.warning_Signal.emit(self.tr("Alist服务未运行，无法打开！"))
            return
        QDesktopServices.openUrl(QUrl(self.alist_url))

    def show_webdav_url(self):
        """显示WebDAV地址信息"""
        if not alistService.is_running or not alistService.port:
            signalBus.warning_Signal.emit(self.tr("请先启动Alist服务！"))
            return

        # 获取局域网IP的逻辑可以放在服务层，但放在这里也无妨
        try:
            import socket

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "N/A"

        msg_box = MessageBox(
            "WebDAV地址",
            (
                f"本机地址：http://127.0.0.1:{alistService.port}/dav\n\n"
                f"局域网地址：http://{local_ip}:{alistService.port}/dav\n\n"
                "注意：WebDAV地址需使用支持此协议的客户端打开，不能直接用浏览器。"
            ),
            self.window(),
        )
        msg_box.setContentCopyable(True)
        msg_box.yesButton.setText("查看WebDAV教程")
        if msg_box.exec():
            QDesktopServices.openUrl(
                QUrl("https://docs.openlist.team/zh/guide/webdav.html")
            )

    # --- 槽函数 (响应服务信号，更新UI) ---

    def on_alist_state_changed(self, is_running: bool, url: str, pid: int):
        """当Alist服务状态改变时更新UI"""
        self.alist_url = url
        if is_running:
            self.start_button.setText(self.tr("停止"))
            self.start_button.setIcon(FIF.PAUSE)
            if not self.alist_info_badge:
                self.alist_info_badge = InfoBadge.success(
                    "运行中",
                    parent=self,
                    target=self.AlistTitleLabel,
                    position=InfoBadgePosition.TOP_RIGHT,
                )
                setFont(self.alist_info_badge, 13)
                self.alist_info_badge.adjustSize()
            self.alist_info_badge.show()
            
            # 检查是否需要在Alist启动后自动启动Rclone
            if cfg.get(cfg.rcloneStartAfterAlist):
                self.append_log("<span style='color: #2196F3;'>[INFO]</span> 检测到Alist启动后自动启动Rclone配置已启用")
                if not rcloneManager.is_core_running:
                    self.append_log("<span style='color: #2196F3;'>[INFO]</span> 正在启动Rclone核心服务...")
                    rcloneManager.start_core_service()
                else:
                    self.append_log("<span style='color: #FFA726;'>[WARN]</span> Rclone核心服务已在运行")
        else:
            self.start_button.setText(self.tr("启动"))
            self.start_button.setIcon(FIF.PLAY)
            if self.alist_info_badge:
                self.alist_info_badge.hide()
                
    def on_alist_startup_params_changed(self):
        """当Alist启动参数改变时，重启服务"""
        if alistService.is_running:
            alistService.restart()

    def append_log(self, html_message: str):
        """将HTML格式的日志添加到文本框"""
        cursor = self.log_text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(html_message + "<br>")
        # 确保滚动到底部
        scrollbar = self.log_text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_password_ready(self, username: str, password: str):
        """当服务获取到密码后，显示消息框"""
        msg_box = MessageBox(
            "管理员信息", f"账号：{username}\n密码：{password}", self.window()
        )
        msg_box.yesButton.setText("复制密码")
        if msg_box.exec():
            QApplication.clipboard().setText(password)
            signalBus.success_Signal.emit("密码已复制到剪贴板!")

    def on_version_ready(self, version_info: str):
        """显示版本信息对话框"""
        msg_box = MessageBox(self.tr("版本信息"), version_info, self.window())
        msg_box.cancelButton.hide()
        msg_box.yesButton.setText(self.tr("我知道了"))
        msg_box.show()

    def on_service_error(self, message: str):
        """处理来自服务的错误信号，在UI上显示"""
        formatted_error = f'<span style="color: #FF4444;">错误: {message}</span>'
        self.append_log(formatted_error)
        signalBus.error_Signal.emit(message)