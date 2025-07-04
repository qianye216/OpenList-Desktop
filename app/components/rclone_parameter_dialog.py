# coding: utf-8
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CheckBox,
    LineEdit,
    MessageBoxBase,
    ScrollArea,
    StrongBodyLabel,
    setFont,
)

from ..common.signal_bus import signalBus


class RcloneParameterDialog(MessageBoxBase):
    """Rclone 启动参数编辑对话框"""

    def __init__(self, current_params: list = None, parent: QWidget = None):
        """
        初始化 Rclone 参数编辑对话框

        :param current_params: list, 当前的参数列表
        :param parent: QWidget, 父窗口
        """
        super().__init__(parent=parent)
        self.current_params = current_params or []

        # 预定义的常用 Rclone 参数
        self.common_params = [
            ("rcd", "启动 RClone 远程控制守护进程", True),
            ("--rc-addr", "RC HTTP 服务器监听地址", "127.0.0.1:5572"),
            ("--rc-user", "RC HTTP 用户名", "admin"),
            ("--rc-pass", "RC HTTP 密码", "admin"),
            ("--rc-web-gui", "启用 Web GUI", False),
            ("--rc-web-gui-no-open-browser", "不自动打开浏览器", True),
            ("--rc-allow-origin", "允许的 CORS 来源", ""),
            ("--log-level", "日志级别", "INFO"),
            ("--log-file", "日志文件路径", ""),
            ("--config", "配置文件路径", ""),
        ]
        
        # 必需的参数，这些参数必须勾选且不能取消
        self.required_params = {"rcd", "--rc-addr", "--rc-user", "--rc-pass"}

        self._initWidget()
        self._initLayout()
        self._loadCurrentParams()

    def _initWidget(self):
        """初始化所有UI组件"""
        self.titleLabel = BodyLabel(self.tr("Rclone 启动参数设置"), self)
        setFont(self.titleLabel, 18)

        # 创建滚动区域
        self.scrollArea = ScrollArea(self)
        self.scrollWidget = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollWidget)
        
        self.scrollLayout.setSpacing(15)
        self.scrollLayout.setAlignment(Qt.AlignmentFlag.AlignTop)  # 设置顶部对齐
        self.scrollLayout.setContentsMargins(10, 10, 10, 10)  # 设置内边距

        # 预定义参数的复选框和输入框
        self.param_widgets = {}

        for param_name, description, default_value in self.common_params:
            # 创建复选框
            checkbox = CheckBox(f"{param_name} - {description}", self)
            
            # 如果是必需参数，设置为默认勾选且禁用
            if param_name in self.required_params:
                checkbox.setChecked(True)
                checkbox.setEnabled(False)  # 禁用复选框，无法取消勾选

            # 如果参数需要值，创建输入框
            if isinstance(default_value, str) and default_value != "":
                input_widget = LineEdit(self)
                input_widget.setPlaceholderText(f"默认: {default_value}")
                input_widget.setText(default_value)
                self.param_widgets[param_name] = (checkbox, input_widget)
            elif isinstance(default_value, str):
                input_widget = LineEdit(self)
                input_widget.setPlaceholderText("可选参数值")
                self.param_widgets[param_name] = (checkbox, input_widget)
            else:
                # 布尔类型参数，只有复选框
                checkbox.setChecked(default_value)
                self.param_widgets[param_name] = (checkbox, None)

        # 自定义参数输入框
        self.customParamsLabel = StrongBodyLabel(self.tr("自定义参数"), self)
        self.customParamsEdit = LineEdit(self)
        self.customParamsEdit.setPlaceholderText(self.tr("额外的参数，用空格分隔"))

    def _initLayout(self):
        """初始化并设置布局"""
        # 添加标题
        self.viewLayout.setSpacing(15)
        self.viewLayout.addWidget(self.titleLabel)

        # 添加所有参数组件到滚动布局中
        for param_name, description, default_value in self.common_params:
            checkbox, input_widget = self.param_widgets[param_name]

            if input_widget:
                # 参数需要值的情况
                param_layout = QVBoxLayout()
                param_layout.setSpacing(5)
                param_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # 设置左对齐
                param_layout.addWidget(checkbox)

                # 缩进输入框
                input_layout = QHBoxLayout()
                input_layout.addSpacing(20)  # 缩进
                input_layout.addWidget(input_widget)
                input_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # 设置左对齐
                param_layout.addLayout(input_layout)

                self.scrollLayout.addLayout(param_layout)
            else:
                # 只有复选框的情况
                self.scrollLayout.addWidget(checkbox)

        # 自定义参数组
        custom_layout = QVBoxLayout()
        custom_layout.setSpacing(8)
        custom_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # 设置左对齐
        custom_layout.addWidget(self.customParamsLabel)
        
        # 自定义参数输入框布局
        custom_input_layout = QHBoxLayout()
        custom_input_layout.addWidget(self.customParamsEdit)
        custom_input_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # 设置左对齐
        custom_layout.addLayout(custom_input_layout)
        
        self.scrollLayout.addLayout(custom_layout)

        # 设置滚动区域
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setMaximumHeight(600)  # 设置最大高度为600px
        self.scrollArea.enableTransparentBackground()
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)

        # 将滚动区域添加到主布局
        self.viewLayout.addWidget(self.scrollArea)

        # 设置窗口和按钮
        self.yesButton.setText(self.tr("保存"))
        self.cancelButton.setText(self.tr("取消"))
        self.widget.setMinimumWidth(520)

    def _loadCurrentParams(self):
        """加载当前参数设置"""
        if not self.current_params:
            return

        # 解析当前参数
        i = 0
        custom_params = []

        while i < len(self.current_params):
            param = self.current_params[i]

            if param in self.param_widgets:
                checkbox, input_widget = self.param_widgets[param]
                # 对于非必需参数才设置勾选状态
                if param not in self.required_params:
                    checkbox.setChecked(True)

                # 如果这个参数需要值，尝试获取下一个参数作为值
                if input_widget and i + 1 < len(self.current_params):
                    next_param = self.current_params[i + 1]
                    # 如果下一个参数不是以 - 开头，认为它是当前参数的值
                    if not next_param.startswith("-"):
                        input_widget.setText(next_param)
                        i += 1  # 跳过这个值参数
            else:
                # 未识别的参数，添加到自定义参数中
                custom_params.append(param)

            i += 1

        # 设置自定义参数
        if custom_params:
            self.customParamsEdit.setText(" ".join(custom_params))

    def validate(self) -> bool:
        """
        验证用户输入
        
        :return: bool, 验证是否通过
        """
        # 检查是否至少选择了 rcd 参数（这个检查现在是多余的，因为rcd已经强制勾选）
        rcd_checkbox, _ = self.param_widgets.get("rcd", (None, None))
        if not rcd_checkbox or not rcd_checkbox.isChecked():
            signalBus.warning_Signal.emit(
                self.tr("Rclone 必须启用 'rcd' 参数才能正常工作")
            )
            return False
            
        # 检查必需参数的输入框是否为空
        required_input_params = ["--rc-addr", "--rc-user", "--rc-pass"]
        for param_name in required_input_params:
            checkbox, input_widget = self.param_widgets.get(param_name, (None, None))
            if input_widget and not input_widget.text().strip():
                param_display_name = {
                    "--rc-addr": "RC HTTP 服务器监听地址",
                    "--rc-user": "RC HTTP 用户名", 
                    "--rc-pass": "RC HTTP 密码"
                }.get(param_name, param_name)
                
                signalBus.warning_Signal.emit(
                    self.tr(f"{param_display_name} 不能为空，请填写有效值")
                )
                return False
                
        return True

    def getSelectedParameters(self) -> list:
        """
        获取选中的参数列表
        
        :return: list, 参数列表
        """
        params = []

        # 处理预定义参数
        for param_name, _, _ in self.common_params:
            checkbox, input_widget = self.param_widgets[param_name]

            if checkbox.isChecked():
                params.append(param_name)

                # 如果有输入框且有值，添加参数值
                if input_widget and input_widget.text().strip():
                    params.append(input_widget.text().strip())

        # 处理自定义参数
        custom_params = self.customParamsEdit.text().strip()
        if custom_params:
            # 简单按空格分割，实际可能需要更复杂的解析
            params.extend(custom_params.split())

        return params
