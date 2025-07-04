from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from qfluentwidgets import (
    AvatarWidget,
    BodyLabel,
    DotInfoBadge,
    ElevatedCardWidget,
    PillPushButton,
    SubtitleLabel,
    ToolTipFilter,
    ToolTipPosition,
    TransparentToolButton,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from ..common.utils import openUrl


class MountCard(ElevatedCardWidget):
    """Rclone挂载卡片组件 (HTTP API 版本)"""

    settingsClicked = Signal()
    deleteClicked = Signal()
    startClicked = Signal()
    stopClicked = Signal()

    def __init__(self, mount_config: dict, parent=None):
        super().__init__(parent=parent)
        self.mount_config = mount_config.copy()
        self.name = self.mount_config.get("name", "N/A")
        self.is_mounted = False
        self.setObjectName(f"MountCard_{self.name.replace(' ', '_')}")

        self._initWidget()
        self._initLayout()
        self._connectSignalToSlot()
        self.setMountedState(False)  # Set initial state

    def _initWidget(self):
        """初始化所有子组件"""
        # 左侧：头像组件
        self.avatar = AvatarWidget(self)
        self.avatar.setText(self.name)  # 使用名称的第一个字符
        self.avatar.setRadius(20)  # 设置一个适合卡片大小的半径 (直径40px)

        # 中间：文字信息
        self.titleLabel = SubtitleLabel(self.name, self)

        # 状态指示器 - 默认为info状态（未挂载）
        self.statusBadge = DotInfoBadge.info(self)
        self.statusBadge.setFixedSize(10, 10)

        # 路径信息区域 - 使用PillPushButton作为标签和BodyLabel显示路径
        self.sourcePathPill = PillPushButton("源路径", self)
        self.sourcePathPill.setEnabled(False)  # 设为不可点击，仅作为标签使用
        self.sourcePathLabel = BodyLabel(self._get_remote_path(), self)

        self.mountPathPill = PillPushButton("挂载路径", self)
        self.mountPathPill.setEnabled(False)  # 设为不可点击，仅作为标签使用
        self.mountPathLabel = BodyLabel(self._get_mount_point(), self)

        # 挂载路径打开按钮
        self.openMountPathButton = TransparentToolButton(FIF.FOLDER, self)
        self.openMountPathButton.setToolTip(self.tr("打开挂载路径"))
        self.openMountPathButton.installEventFilter(
            ToolTipFilter(
                self.openMountPathButton, showDelay=300, position=ToolTipPosition.TOP
            )
        )
        self.openMountPathButton.setVisible(False)

        # 右侧：控制按钮
        self.settingsButton = TransparentToolButton(FIF.SETTING, self)
        self.settingsButton.setToolTip(self.tr("设置"))
        self.settingsButton.installEventFilter(
            ToolTipFilter(
                self.settingsButton, showDelay=300, position=ToolTipPosition.TOP
            )
        )

        self.deleteButton = TransparentToolButton(FIF.DELETE, self)
        self.deleteButton.setToolTip(self.tr("删除"))
        self.deleteButton.installEventFilter(
            ToolTipFilter(
                self.deleteButton, showDelay=300, position=ToolTipPosition.TOP
            )
        )

        self.toggleMountButton = TransparentToolButton(FIF.PLAY, self)
        self.toggleMountButton.setToolTip(self.tr("启动 (挂载)"))
        self.toggleMountButton.installEventFilter(
            ToolTipFilter(
                self.toggleMountButton, showDelay=300, position=ToolTipPosition.TOP
            )
        )

    def _initLayout(self):
        """初始化布局"""
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setContentsMargins(12, 12, 12, 12)
        self.hBoxLayout.setSpacing(12)

        self.textLayout = QVBoxLayout()
        self.titleLayout = QHBoxLayout()
        self.titleLayout.setSpacing(8)
        self.titleLayout.addWidget(self.titleLabel)
        self.titleLayout.addWidget(self.statusBadge)
        self.titleLayout.addStretch(1)

        self.pathLayout = QVBoxLayout()
        self.pathLayout.setSpacing(4)

        # 源路径行
        sourceRow = QHBoxLayout()
        sourceRow.setSpacing(8)
        sourceRow.addWidget(self.sourcePathPill)
        sourceRow.addWidget(self.sourcePathLabel, 1)
        self.pathLayout.addLayout(sourceRow)

        # 挂载路径行（添加打开按钮）
        mountRow = QHBoxLayout()
        mountRow.setSpacing(8)
        mountRow.addWidget(self.mountPathPill)
        mountRow.addWidget(self.mountPathLabel)
        mountRow.addWidget(self.openMountPathButton)
        mountRow.addStretch()
        self.pathLayout.addLayout(mountRow)

        self.textLayout.addLayout(self.titleLayout)
        self.textLayout.addLayout(self.pathLayout)
        self.textLayout.setSpacing(8)

        self.hBoxLayout.addWidget(self.avatar)
        self.hBoxLayout.addLayout(self.textLayout, 1)
        self.hBoxLayout.addWidget(self.settingsButton)
        self.hBoxLayout.addWidget(self.deleteButton)
        self.hBoxLayout.addWidget(self.toggleMountButton)

    def _connectSignalToSlot(self):
        """连接信号和槽"""
        self.settingsButton.clicked.connect(self.settingsClicked)
        self.deleteButton.clicked.connect(self.deleteClicked)
        self.toggleMountButton.clicked.connect(self._onToggleMount)
        self.openMountPathButton.clicked.connect(self._onOpenMountPath)

    def _onToggleMount(self):
        """切换挂载状态"""
        if self.is_mounted:
            self.stopClicked.emit()
        else:
            self.startClicked.emit()

    def _onOpenMountPath(self):
        """打开挂载路径"""
        if not self.is_mounted:
            return

        mount_path = self._get_mount_point()
        if mount_path == "N/A":
            return

        openUrl(mount_path)

    def _get_remote_path(self) -> str:
        return self.mount_config.get("fs", self.mount_config.get("remote_path", "N/A"))

    def getMountPoint(self) -> str:
        return self.mount_config.get("mount_point", "N/A")

    def setMountedState(self, mounted: bool):
        """
        设置挂载状态，同时控制设置按钮的启用/禁用状态

        :param mounted: bool, 是否已挂载
        """
        if self.is_mounted == mounted:
            return

        self.is_mounted = mounted

        self.statusBadge.deleteLater()

        if mounted:
            self.statusBadge = DotInfoBadge.success(self)
            self.toggleMountButton.setIcon(FIF.PAUSE)
            self.toggleMountButton.setToolTip(self.tr("停止 (卸载)"))
            # 已挂载时禁用设置按钮，启用打开挂载路径按钮
            self.settingsButton.setEnabled(False)
            self.deleteButton.setEnabled(False)
            self.openMountPathButton.setVisible(True)
        else:
            self.statusBadge = DotInfoBadge.info(self)
            self.toggleMountButton.setIcon(FIF.PLAY)
            self.toggleMountButton.setToolTip(self.tr("启动 (挂载)"))
            # 未挂载时启用设置按钮，禁用打开挂载路径按钮
            self.settingsButton.setEnabled(True)
            self.deleteButton.setEnabled(True)
            self.openMountPathButton.setVisible(False)

        self.statusBadge.setFixedSize(10, 10)
        self.titleLayout.insertWidget(
            1, self.statusBadge, 0, Qt.AlignmentFlag.AlignLeft
        )

    def _get_mount_point(self) -> str:
        """
        获取挂载点路径

        :return: str, 挂载点路径
        """
        if self.mount_config:
            return self.mount_config.get(
                "mount_point", self.mount_config.get("mountPoint", "N/A")
            )

        return "N/A"

    def getMountConfig(self) -> dict:
        return self.mount_config.copy()

    def updateMountConfig(self, mount_config: dict):
        self.mount_config = mount_config.copy()
        self.name = self.mount_config.get("name", self.name)
        self.titleLabel.setText(self.name)
        self.avatar.setText(self.name)
        print("源路径：", self._get_remote_path(),self._get_remote_path().lstrip("webdav:"))
        self.sourcePathLabel.setText(self._get_remote_path())
        self.mountPathLabel.setText(self.getMountPoint())
