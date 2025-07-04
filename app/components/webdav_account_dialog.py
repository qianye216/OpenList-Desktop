# coding: utf-8
import httpx
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    LineEdit,
    MessageBoxBase,
    PasswordLineEdit,
    PushButton,
    StrongBodyLabel,
    setFont,
)
from qfluentwidgets import FluentIcon as FIF

from ..common.concurrent import TaskExecutor
from ..common.signal_bus import signalBus


class WebDavAccountDialog(MessageBoxBase):
    """WebDAV 账户配置对话框"""

    def __init__(self, current_config: dict = None, parent: QWidget = None):
        """
        初始化 WebDAV 账户配置对话框

        :param current_config: dict, 当前的配置信息
        :param parent: QWidget, 父窗口
        """
        super().__init__(parent=parent)
        self.current_config = current_config or {}

        self._initWidget()
        self._initLayout()

    def _initWidget(self):
        """初始化所有UI组件"""
        self.titleLabel = BodyLabel(self.tr("WebDAV 账户配置"), self)
        setFont(self.titleLabel, 18)

        # URL 设置
        self.urlLabel = StrongBodyLabel(self.tr("WebDAV 服务地址"), self)
        self.urlEdit = LineEdit(self)
        self.urlEdit.setPlaceholderText(self.tr("例如: http://localhost:5244/dav"))
        self.urlEdit.setClearButtonEnabled(True)
        self.urlEdit.setText(
            self.current_config.get("url", "http://localhost:5244/dav")
        )

        # 用户名设置
        self.userLabel = StrongBodyLabel(self.tr("用户名"), self)
        self.userEdit = LineEdit(self)
        self.userEdit.setPlaceholderText(self.tr("WebDAV 用户名"))
        self.userEdit.setClearButtonEnabled(True)
        self.userEdit.setText(self.current_config.get("user", "admin"))

        # 密码设置
        self.passwordLabel = StrongBodyLabel(self.tr("密码"), self)
        self.passwordEdit = PasswordLineEdit(self)
        self.passwordEdit.setPlaceholderText(self.tr("WebDAV 密码"))
        self.passwordEdit.setClearButtonEnabled(True)
        self.passwordEdit.setText(self.current_config.get("pass", "admin"))

    def _initLayout(self):
        """初始化并设置布局"""
        self.viewLayout.setSpacing(20)
        self.viewLayout.addWidget(self.titleLabel)

        # URL 组
        urlLayout = self._create_labeled_input_layout(self.urlLabel, self.urlEdit)
        self.viewLayout.addLayout(urlLayout)

        # 用户名组
        userLayout = self._create_labeled_input_layout(self.userLabel, self.userEdit)
        self.viewLayout.addLayout(userLayout)

        # 密码组
        passwordLayout = self._create_labeled_input_layout(
            self.passwordLabel, self.passwordEdit
        )
        self.viewLayout.addLayout(passwordLayout)

        # 测试连接按钮
        self.testButton = PushButton(self.tr("测试连接"), self)
        self.testButton.setIcon(FIF.CONNECT)
        self.testButton.clicked.connect(self._test_connection)

        # 添加测试按钮到布局
        test_layout = QHBoxLayout()
        test_layout.addStretch()
        test_layout.addWidget(self.testButton)
        self.viewLayout.addLayout(test_layout)

        # 设置窗口和按钮
        self.yesButton.setText(self.tr("保存"))
        self.cancelButton.setText(self.tr("取消"))
        self.widget.setMinimumWidth(420)

    def _create_labeled_input_layout(self, label: QWidget, input_widget: QWidget):
        """创建一个包含标签和输入框的垂直布局"""
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.addWidget(label)
        layout.addWidget(input_widget)
        return layout

    def validate(self) -> bool:
        """验证用户输入"""
        url = self.urlEdit.text().strip()
        user = self.userEdit.text().strip()
        password = self.passwordEdit.text().strip()

        if not all([url, user, password]):
            signalBus.warning_Signal.emit(self.tr("URL、用户名和密码不能为空"))
            return False

        return True

    def get_config(self) -> dict:
        """获取配置信息"""
        return {
            "url": self.urlEdit.text().strip(),
            "user": self.userEdit.text().strip(),
            "pass": self.passwordEdit.text().strip(),
            "vendor": "other",
        }

    def _test_connection(self):
        """测试 WebDAV 连接"""
        url = self.urlEdit.text().strip()
        user = self.userEdit.text().strip()
        password = self.passwordEdit.text().strip()

        if not all([url, user, password]):
            signalBus.warning_Signal.emit(self.tr("请先填写完整的连接信息"))
            return

        # 禁用测试按钮防止重复点击
        self.testButton.setEnabled(False)
        self.testButton.setText(self.tr("测试中..."))

        def test_webdav_connection(url, user, password):
            """WebDAV连接测试函数"""
            try:
                # 设置WebDAV请求头
                headers = {
                    "User-Agent": "OpenList-Desktop/1.0",
                    "Content-Type": "application/xml; charset=utf-8",
                    "Depth": "0",
                }

                # 直接使用PROPFIND请求测试连接，它能验证认证信息
                with httpx.Client() as client:
                    response = client.request(
                        "PROPFIND",
                        url,
                        auth=(user, password),
                        headers=headers,
                        timeout=10,
                    )

                if response.status_code in [200, 207]:  # 207是WebDAV的Multi-Status响应
                    return {"success": True, "message": "WebDAV 连接成功！"}
                elif response.status_code == 401:
                    return {"success": False, "message": "认证失败：用户名或密码错误"}
                elif response.status_code == 403:
                    return {
                        "success": False,
                        "message": "权限不足：请检查用户权限或URL路径",
                    }
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "message": "路径不存在：请检查WebDAV服务器URL",
                    }
                else:
                    return {
                        "success": False,
                        "message": f"连接失败: HTTP {response.status_code}\n响应: {response.text[:200]}",
                    }

            except Exception as e:
                return {"success": False, "message": f"连接失败: {str(e)}"}

        # 执行异步任务并处理结果
        TaskExecutor.runTask(test_webdav_connection, url, user, password).then(
            lambda result: self._on_test_finished(result["success"], result["message"])
        )

    def _on_test_finished(self, success: bool, message: str):
        """测试完成回调"""
        # 恢复按钮状态
        self.testButton.setEnabled(True)
        self.testButton.setText(self.tr("测试连接"))

        # 显示结果
        if success:
            signalBus.success_Signal.emit(message)
        else:
            signalBus.warning_Signal.emit(message)
