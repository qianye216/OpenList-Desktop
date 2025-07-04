# coding:utf-8

from PySide6.QtWidgets import QFileDialog, QHBoxLayout
from qfluentwidgets import (
    BodyLabel,
    CheckBox,
    LineEdit,
    MessageBoxBase,
    PrimaryPushButton,
    StrongBodyLabel,
    setFont,
)


class AlistParameterDialog(MessageBoxBase):
    """
    Alist启动参数配置对话框
    - 优化了UI布局，将部分参数组改为水平排列
    - 移除了参数说明标签，使界面更简洁
    - 保持了所有核心功能（互斥选择、路径选择等）
    """

    def __init__(self, current_params: list[str] = [], parent=None):
        """
        初始化Alist参数对话框

        Args:
            parent: 父窗口
        """
        super().__init__(parent)

        self.setupUI()
        self.connect_signals()
        self._parse_and_set_params(current_params)

    def setupUI(self):
        """
        设置用户界面布局
        """
        self.titleLabel = BodyLabel("OpenList 启动参数", self)
        setFont(self.titleLabel, 18)
        self.viewLayout.addWidget(self.titleLabel)
        # --- 数据目录参数组 ---
        self.viewLayout.addWidget(StrongBodyLabel("数据目录参数 (互斥)"))
        data_layout = QHBoxLayout()
        self.data_checkbox = CheckBox("--data")
        self.data_checkbox.setEnabled(False)  # 初始时路径为空，禁用
        self.data_path_edit = LineEdit()
        self.data_path_edit.setPlaceholderText("请输入或选择数据文件夹路径")
        self.browse_button = PrimaryPushButton("浏览...")
        data_layout.addWidget(self.data_checkbox)
        data_layout.addWidget(self.data_path_edit)
        data_layout.addWidget(self.browse_button)
        self.viewLayout.addLayout(data_layout)

        self.force_bin_dir_checkbox = CheckBox("--force-bin-dir")
        self.viewLayout.addWidget(self.force_bin_dir_checkbox)

        # --- 调试模式参数组 (水平布局) ---
        self.viewLayout.addSpacing(15)
        self.viewLayout.addWidget(StrongBodyLabel("调试模式参数 (互斥)"))
        debug_layout = QHBoxLayout()
        self.debug_checkbox = CheckBox("--debug")
        self.dev_checkbox = CheckBox("--dev")
        debug_layout.addWidget(self.debug_checkbox)
        debug_layout.addWidget(self.dev_checkbox)
        self.viewLayout.addLayout(debug_layout)

        # --- 其他参数组 (水平布局) ---
        self.viewLayout.addSpacing(15)
        self.viewLayout.addWidget(StrongBodyLabel("其他参数"))
        other_params_layout = QHBoxLayout()
        self.log_std_checkbox = CheckBox("--log-std")
        self.no_prefix_checkbox = CheckBox("--no-prefix")
        other_params_layout.addWidget(self.log_std_checkbox)
        other_params_layout.addWidget(self.no_prefix_checkbox)
        self.viewLayout.addLayout(other_params_layout)

        # 设置按钮和窗口宽度
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(500)

    def connect_signals(self):
        """连接所有组件的信号与槽"""
        # --data 路径输入框文本变化
        self.data_path_edit.textChanged.connect(self._on_data_path_changed)
        # 浏览按钮点击
        self.browse_button.clicked.connect(self._on_browse_clicked)

        # 数据目录互斥逻辑
        self.data_checkbox.toggled.connect(self._on_data_toggled)
        self.force_bin_dir_checkbox.toggled.connect(self._on_force_bin_dir_toggled)

        # 调试模式互斥逻辑
        self.debug_checkbox.toggled.connect(self._on_debug_toggled)
        self.dev_checkbox.toggled.connect(self._on_dev_toggled)

    def _parse_and_set_params(self, params: list[str]):
        """
        解析参数字符串并设置UI组件的初始状态
        """
        if not params:
            return

        params_list = params
        i = 0
        while i < len(params_list):
            param = params_list[i]
            if param == "--data":
                # --data 后面必须跟一个路径值
                if i + 1 < len(params_list):
                    path = params_list[i + 1]
                    self.data_path_edit.setText(path)
                    # setText会触发_on_data_path_changed, 从而启用复选框
                    self.data_checkbox.setChecked(True)
                    i += 1  # 跳过路径值，处理下一个参数
            elif param == "--force-bin-dir":
                self.force_bin_dir_checkbox.setChecked(True)
            elif param == "--debug":
                self.debug_checkbox.setChecked(True)
            elif param == "--dev":
                self.dev_checkbox.setChecked(True)
            elif param == "--log-std":
                self.log_std_checkbox.setChecked(True)
            elif param == "--no-prefix":
                self.no_prefix_checkbox.setChecked(True)

            i += 1  # 移至下一个参数

    def _on_data_path_changed(self, text: str):
        """当 --data 路径文本变化时的处理"""
        is_empty = not text.strip()
        self.data_checkbox.setEnabled(not is_empty)
        if is_empty:
            self.data_checkbox.setChecked(False)

    def _on_browse_clicked(self):
        """点击浏览按钮选择文件夹"""
        path = QFileDialog.getExistingDirectory(self, "选择数据文件夹", "")
        if path:
            self.data_path_edit.setText(path)

    def _on_data_toggled(self, checked: bool):
        """当 --data 复选框状态改变"""
        if checked:
            self.force_bin_dir_checkbox.blockSignals(True)
            self.force_bin_dir_checkbox.setChecked(False)
            self.force_bin_dir_checkbox.blockSignals(False)

    def _on_force_bin_dir_toggled(self, checked: bool):
        """当 --force-bin-dir 复选框状态改变"""
        if checked:
            self.data_checkbox.blockSignals(True)
            self.data_checkbox.setChecked(False)
            self.data_checkbox.blockSignals(False)

    def _on_debug_toggled(self, checked: bool):
        """当 --debug 复选框状态改变"""
        if checked:
            self.dev_checkbox.blockSignals(True)
            self.dev_checkbox.setChecked(False)
            self.dev_checkbox.blockSignals(False)

    def _on_dev_toggled(self, checked: bool):
        """当 --dev 复选框状态改变"""
        if checked:
            self.debug_checkbox.blockSignals(True)
            self.debug_checkbox.setChecked(False)
            self.debug_checkbox.blockSignals(False)

    def getSelectedParameters(self) -> list[str]:
        """
        获取选中的参数列表

        Returns:
            list[str]: 选中的参数列表，例如: ['--data', '/path/to/data', '--debug']
        """
        parameters = []

        if self.data_checkbox.isChecked():
            path = self.data_path_edit.text().strip()
            if path:
                parameters.extend(["--data", path])

        if self.force_bin_dir_checkbox.isChecked():
            parameters.append("--force-bin-dir")

        if self.debug_checkbox.isChecked():
            parameters.append("--debug")

        if self.dev_checkbox.isChecked():
            parameters.append("--dev")

        if self.log_std_checkbox.isChecked():
            parameters.append("--log-std")

        if self.no_prefix_checkbox.isChecked():
            parameters.append("--no-prefix")

        return parameters
