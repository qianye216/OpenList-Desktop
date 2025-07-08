# file: common/components/add_mount_dialog.py
import os
import sys
from typing import Optional

from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CheckBox,
    FluentIcon,
    TransparentToolButton,
    LineEdit,
    MessageBoxBase,
    RadioButton,
    StrongBodyLabel,
    ToolButton,
    setFont,
)

from ..common.config import cfg
from ..common.signal_bus import signalBus
from .first_mount_tip_dialog import FirstMountTipDialog


class AddMountDialog(MessageBoxBase):
    """添加或编辑挂载配置的对话框 (HTTP API 版本)"""

    def __init__(self, mount_config: Optional[dict] = None, parent: QWidget = None):
        super().__init__(parent=parent)
        self.is_edit_mode = mount_config is not None
        self.original_name = mount_config.get("name") if self.is_edit_mode else None
        self._initWidget()
        self._initLayout()
        self._connectSignalToSlot()

        if self.is_edit_mode and mount_config:
            self.populate_form(mount_config)

    def _initWidget(self):
        """初始化所有UI组件"""
        # 根据编辑模式设置标题
        title_text = self.tr("编辑挂载") if self.is_edit_mode else self.tr("创建挂载")
        self.titleLabel = BodyLabel(title_text, self)
        setFont(self.titleLabel, 18)

        # 先决条件按钮
        self.prerequisiteButton = TransparentToolButton(FluentIcon.HELP, parent=self)

        # 挂载名称
        self.nameLabel = StrongBodyLabel(self.tr("挂载名称"), self)
        self.nameEdit = LineEdit(self)
        self.nameEdit.setPlaceholderText(self.tr("唯一的挂载名称, e.g., MyOnedrive"))
        self.nameEdit.setClearButtonEnabled(True)

        # 源路径
        self.remotePathLabel = StrongBodyLabel(self.tr("源路径"), self)
        self.remotePathEdit = LineEdit(self)
        self.remotePathEdit.setPlaceholderText(
            self.tr("在alist中的路径，如根目录为`/`")
        )
        self.remotePathEdit.setClearButtonEnabled(True)

        # 目标路径
        self.mountPointLabel = StrongBodyLabel(self.tr("目标路径"), self)
        self.mountPointEdit = LineEdit(self)
        placeholder = (
            self.tr("你要挂载到的位置，如 /Users/yourname/MyCloud")
            if sys.platform == "darwin"
            else self.tr("你要挂载到的位置，如在Windows中挂载到一个新的盘为`S:`")
        )
        self.mountPointEdit.setPlaceholderText(placeholder)
        self.mountPointEdit.setClearButtonEnabled(True)

        self.browseButton = None
        if sys.platform == "darwin":
            self.browseButton = ToolButton(FluentIcon.FOLDER, self)
            self.browseButton.setToolTip(self.tr("浏览本地目录"))

        # 启动时自动挂载 和 网络模式
        self.autoMountCheckBox = CheckBox(self.tr("启动时自动挂载"), self)
        self.networkModeCheckBox = CheckBox(self.tr("网络模式"), self)
        self.autoMountCheckBox.setChecked(False)
        self.networkModeCheckBox.setChecked(True)

        # 缓存模式
        self.cacheModeLabel = StrongBodyLabel(self.tr("缓存模式"), self)
        self.cacheModeGroup = QButtonGroup(self)
        self.cacheOffRadio = RadioButton(self.tr("关闭"), self)
        self.cacheMinimalRadio = RadioButton(self.tr("最小"), self)
        self.cacheWritesRadio = RadioButton(self.tr("写入"), self)
        self.cacheFullRadio = RadioButton(self.tr("完全"), self)

        self.cacheModeGroup.addButton(self.cacheOffRadio, 0)
        self.cacheModeGroup.addButton(self.cacheMinimalRadio, 1)
        self.cacheModeGroup.addButton(self.cacheWritesRadio, 2)
        self.cacheModeGroup.addButton(self.cacheFullRadio, 3)
        self.cacheOffRadio.setChecked(True)

        # 自定义参数
        self.extraArgsLabel = StrongBodyLabel(self.tr("额外参数"), self)
        self.extraArgsEdit = LineEdit(self)
        self.extraArgsEdit.setPlaceholderText(
            self.tr("参考 https://rclone.org/commands/rclone_mount/")
        )
        self.extraArgsEdit.setClearButtonEnabled(True)

    def _initLayout(self):
        """初始化并设置布局"""
        self.viewLayout.setSpacing(20)

        # 标题和先决条件按钮的水平布局
        titleLayout = QHBoxLayout()
        titleLayout.addWidget(self.titleLabel)
        titleLayout.addWidget(self.prerequisiteButton)
        titleLayout.setSpacing(0)
        titleLayout.addStretch(1)
        self.viewLayout.addLayout(titleLayout)

        # 挂载名称组
        nameLayout = self._create_labeled_input_layout(self.nameLabel, self.nameEdit)
        self.viewLayout.addLayout(nameLayout)

        # 源路径组
        remotePathLayout = self._create_labeled_input_layout(
            self.remotePathLabel, self.remotePathEdit
        )
        self.viewLayout.addLayout(remotePathLayout)

        # 目标路径组
        mountPointLayout = QVBoxLayout()
        mountPointLayout.setSpacing(8)
        mountPointLayout.addWidget(self.mountPointLabel)
        mountPointInputLayout = QHBoxLayout()
        mountPointInputLayout.addWidget(self.mountPointEdit)
        if self.browseButton:
            mountPointInputLayout.addWidget(self.browseButton)
        mountPointLayout.addLayout(mountPointInputLayout)
        self.viewLayout.addLayout(mountPointLayout)

        # 复选框水平布局
        checkboxLayout = QHBoxLayout()
        checkboxLayout.addWidget(self.autoMountCheckBox)
        checkboxLayout.addStretch(1)
        checkboxLayout.addWidget(self.networkModeCheckBox)
        self.viewLayout.addLayout(checkboxLayout)

        # 优化 1: 将缓存模式也用垂直布局包裹起来
        cacheModeVLayout = QVBoxLayout()
        cacheModeVLayout.setSpacing(8)
        cacheModeVLayout.addWidget(self.cacheModeLabel)

        cacheRadioHLayout = QHBoxLayout()
        cacheRadioHLayout.addWidget(self.cacheOffRadio)
        cacheRadioHLayout.addWidget(self.cacheMinimalRadio)
        cacheRadioHLayout.addWidget(self.cacheWritesRadio)
        cacheRadioHLayout.addWidget(self.cacheFullRadio)

        cacheModeVLayout.addLayout(cacheRadioHLayout)
        self.viewLayout.addLayout(cacheModeVLayout)

        # 自定义参数组
        extraArgsLayout = self._create_labeled_input_layout(
            self.extraArgsLabel, self.extraArgsEdit
        )
        self.viewLayout.addLayout(extraArgsLayout)

        # 设置窗口和按钮
        # 根据编辑模式设置按钮文本
        button_text = self.tr("保存") if self.is_edit_mode else self.tr("添加")
        self.yesButton.setText(button_text)
        self.cancelButton.setText(self.tr("取消"))
        self.widget.setMinimumWidth(520)

    def _create_labeled_input_layout(
        self, label: QWidget, input_widget: QWidget
    ) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.addWidget(label)
        layout.addWidget(input_widget)
        return layout

    def _connectSignalToSlot(self):
        """连接信号和槽函数"""
        if self.browseButton:
            self.browseButton.clicked.connect(self._onBrowseButtonClicked)
        self.prerequisiteButton.clicked.connect(self._onPrerequisiteButtonClicked)

    def _onBrowseButtonClicked(self):
        """浏览按钮点击事件处理"""
        directory = QFileDialog.getExistingDirectory(
            self,
            self.tr("选择挂载目录"),
            self.mountPointEdit.text() or os.path.expanduser("~"),
        )
        if directory:
            self.mountPointEdit.setText(directory)

    def _onPrerequisiteButtonClicked(self):
        """先决条件按钮点击事件处理"""
        dialog = FirstMountTipDialog(self)
        dialog.exec()

    # --- 修正点：添加回这个被遗漏的方法 ---
    def populate_form(self, config: dict):
        """用现有配置填充表单"""
        self.nameEdit.setText(config.get("name", ""))
        self.remotePathEdit.setText(config.get("remote_path", ""))
        self.mountPointEdit.setText(config.get("mount_point", ""))
        self.autoMountCheckBox.setChecked(config.get("auto_mount", False))
        self.networkModeCheckBox.setChecked(config.get("network_mode", True))
        self.extraArgsEdit.setText(config.get("extra_args", ""))

        cache_mode_id = {"off": 0, "minimal": 1, "writes": 2, "full": 3}.get(
            config.get("vfs_cache_mode", "off"), 0
        )
        self.cacheModeGroup.button(cache_mode_id).setChecked(True)

    def validate(self) -> bool:
        """表单验证"""
        name = self.nameEdit.text().strip()
        remote_path = self.remotePathEdit.text().strip()
        mount_point = self.mountPointEdit.text().strip()

        if not all([name, remote_path, mount_point]):
            signalBus.warning_Signal.emit(
                self.tr("挂载名称、源路径和目标路径不能为空。")
            )
            return False

        # 如果是编辑模式，且名称未改变，则跳过唯一性检查
        if self.is_edit_mode and name == self.original_name:
            return True

        # 检查新名称是否已存在
        existing_names = [c.get("name") for c in cfg.get(cfg.mountConfigs) or []]
        if name in existing_names:
            signalBus.warning_Signal.emit(
                self.tr(f"挂载名称 '{name}' 已存在，请使用唯一的名称。")
            )
            return False

        return True

    def get_mount_config(self) -> dict:
        """获取用户输入的挂载配置"""
        import platform
        
        cache_mode_map = {0: "off", 1: "minimal", 2: "writes", 3: "full"}
        remote_path = self.remotePathEdit.text().strip()
        
        # Windows路径处理：统一使用正斜杠
        if platform.system() == "Windows":
            remote_path = remote_path.replace("\\", "/")

        # 构建fs路径，确保格式正确
        if remote_path and remote_path != "/":
            # 确保路径以斜杠开头
            if not remote_path.startswith("/"):
                remote_path = "/" + remote_path
            fs_path = f"webdav:{remote_path}"
        else:
            fs_path = "webdav:/"

        return {
            "name": self.nameEdit.text().strip(),
            "remote_path": remote_path,
            "mount_point": self.mountPointEdit.text().strip(),
            "auto_mount": self.autoMountCheckBox.isChecked(),
            "network_mode": self.networkModeCheckBox.isChecked(),  # 保留字段
            "vfs_cache_mode": cache_mode_map.get(
                self.cacheModeGroup.checkedId(), "off"
            ),
            "extra_args": self.extraArgsEdit.text().strip(),
            "fs": fs_path,
        }
