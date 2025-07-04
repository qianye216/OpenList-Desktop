# file: ui/mount_interface.py
import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    Action,
    InfoBadge,
    InfoBadgePosition,
    LargeTitleLabel,
    MessageBox,
    PrimaryDropDownPushButton,
    PrimaryPushButton,
    RoundMenu,
    ScrollArea,
    setFont,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from ..common.concurrent import TaskExecutor
from ..common.config import cfg
from ..common.signal_bus import signalBus
from ..components.add_mount_dialog import AddMountDialog
from ..components.empty_state_widget import EmptyStateWidget
from ..components.first_mount_tip_dialog import FirstMountTipDialog  # 新增导入
from ..components.link_buttons_card import LinkButtonsCard
from ..components.mount_card import MountCard
from ..components.rclone_log_dialog import RcloneLogDialog
from ..services.rclone_manager import rcloneManager


class MountInterface(QWidget):
    """Rclone挂载界面类 (HTTP API 版本)"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("MountInterface")

        self.mount_cards: dict[str, MountCard] = {}  # {config_name: card}
        self.rclone_info_badge: Optional[InfoBadge] = None

        self._initWidget()
        self._initLayout()
        self._connectSignalToSlot()
        self._load_mount_cards_from_config()
        self._check_rclone_service_status()
        self._update_empty_state()

    def _initWidget(self):
        """初始化组件"""
        self.vboxLayout = QVBoxLayout(self)

        # 大标题
        self.mountTitleLabel = LargeTitleLabel("Rclone挂载", self)
        self.mountTitleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 控制按钮
        self.start_button = PrimaryPushButton(self.tr("启动"), self)
        self.start_button.setIcon(FIF.PLAY)

        self.add_mount_button = PrimaryPushButton(self.tr("添加挂载"), self)
        self.add_mount_button.setIcon(FIF.ADD)

        # 查看日志按钮（从更多菜单移出）
        self.log_button = PrimaryPushButton(self.tr("查看日志"), self)
        self.log_button.setIcon(FIF.DOCUMENT)

        # 更多按钮（下拉菜单）
        self.more_button = PrimaryDropDownPushButton(self.tr("更多"), self)
        self.more_button.setIcon(FIF.MORE)

        # 创建更多菜单
        self._initMoreMenu()

        # 挂载卡片滚动区域
        self.scroll_area = ScrollArea(self)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)

        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.enableTransparentBackground()
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_layout.addStretch(1)  # Add a stretch to push cards to the top

        self.scroll_area.setMinimumHeight(200)

        # 底部链接按钮卡片
        self.link_buttons_card = LinkButtonsCard(self)

    def _initMoreMenu(self):
        """初始化更多菜单"""
        menu = RoundMenu(parent=self)

        # 只保留查看版本功能
        menu.addAction(
            Action(FIF.FLAG, self.tr("查看版本"), triggered=self.show_rclone_version)
        )

        self.more_button.setMenu(menu)

    def _initLayout(self):
        """初始化布局"""
        # 标题布局
        title_layout = QHBoxLayout()
        title_layout.addStretch()
        title_layout.addWidget(self.mountTitleLabel)
        title_layout.addStretch()

        # 按钮布局 - 重新组织按钮顺序
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.add_mount_button)
        button_layout.addWidget(self.log_button)  # 查看日志按钮移到这里
        button_layout.addWidget(self.more_button)

        # 主布局
        self.vboxLayout.setSpacing(20)
        self.vboxLayout.setContentsMargins(16, 20, 16, 20)
        self.vboxLayout.addLayout(title_layout)
        self.vboxLayout.addLayout(button_layout)
        self.vboxLayout.addWidget(self.scroll_area)
        self.vboxLayout.addWidget(self.link_buttons_card)

    def _connectSignalToSlot(self):
        """连接信号和槽函数"""
        self.start_button.clicked.connect(self.toggle_rclone_service)
        self.add_mount_button.clicked.connect(self.add_mount_config)
        self.log_button.clicked.connect(self.show_rclone_logs)  # 连接查看日志按钮

        # 连接 rclone_manager 的信号
        rcloneManager.coreServiceStateChanged.connect(
            self.on_core_service_state_changed
        )
        # 新增：连接rclone配置需求信号
        rcloneManager.configurationRequired.connect(
            self.handle_rclone_configuration_required
        )
        rcloneManager.mountsInfoUpdated.connect(self.on_mounts_info_updated)
        # rcloneManager.logMessageReady.connect(self.on_log_message)
        # rcloneManager.errorOccurred.connect(self.on_error_occurred)

    def _load_mount_cards_from_config(self):
        # 清空现有卡片
        for card in self.mount_cards.values():
            card.deleteLater()
        self.mount_cards.clear()

        # 重新加载
        for config in cfg.get(cfg.mountConfigs) or []:
            self.add_mount_card(config)
        self._update_empty_state()

    def _update_empty_state(self):
        has_cards = bool(self.mount_cards)
        if not has_cards and not hasattr(self, "empty_state"):
            self.empty_state = EmptyStateWidget(
                title=self.tr("无可用挂载"),
                description=self.tr("请点击 '添加挂载' 按钮进行配置"),
            )
            self.scroll_layout.insertWidget(
                0, self.empty_state, 0, Qt.AlignmentFlag.AlignCenter
            )

        if hasattr(self, "empty_state"):
            self.empty_state.setVisible(not has_cards)

    def handle_rclone_configuration_required(self):
        """
        处理Rclone配置请求，显示配置对话框并导航到设置页面
        """
        # 隐藏加载动画
        signalBus.hideLoadingSig.emit()
        
        message_box = MessageBox(
            "温馨提示", "请先配置好Rclone的工作目录", self.window()
        )
        if message_box.exec():
            self.window().switchTo(self.window().settingInterface)
            self.window().settingInterface.switchTo(3)  # 切换到Rclone设置页面

    def add_mount_card(self, mount_config: dict):
        config_name = mount_config.get("name")
        if not config_name or config_name in self.mount_cards:
            return

        card = MountCard(mount_config, self)
        card.deleteClicked.connect(lambda c=card: self.remove_mount_card(c))
        card.settingsClicked.connect(lambda c=card: self.on_settings_clicked(c))
        card.startClicked.connect(lambda c=card: self.on_start_clicked(c))
        card.stopClicked.connect(lambda c=card: self.on_stop_clicked(c))

        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, card)
        self.mount_cards[config_name] = card
        self._update_empty_state()

    def remove_mount_card(self, card: MountCard):
        """
        删除挂载配置卡片，同时删除对应的远程配置

        :param card: MountCard, 要删除的挂载卡片
        """
        m = MessageBox(
            self.tr("确认删除"),
            self.tr(
                f"您确定要删除挂载配置 '{card.name}' 吗?\n\n注意：这将同时删除对应的远程配置。"
            ),
            self.window(),
        )
        if not m.exec():
            return

        # 如果已挂载，先卸载
        if card.is_mounted:
            self.on_stop_clicked(card)

        # 删除本地配置
        current_configs = cfg.get(cfg.mountConfigs) or []
        updated_configs = [c for c in current_configs if c.get("name") != card.name]
        cfg.set(cfg.mountConfigs, updated_configs)

        # 删除对应的远程配置
        if rcloneManager.is_core_running:
            # 获取挂载配置中的远程名称
            mount_config = next(
                (c for c in current_configs if c.get("name") == card.name), None
            )
            if mount_config and mount_config.get("fs"):
                # 从 fs 字段中提取远程名称 (格式通常是 "remote_name:path")
                fs_value = mount_config["fs"]
                if ":" in fs_value:
                    remote_name = fs_value.split(":")[0]
                    # 删除远程配置
                    result = rcloneManager.delete_remote(remote_name)
                    if result["success"]:
                        signalBus.success_Signal.emit(
                            f"远程配置 '{remote_name}' 已删除"
                        )
                    else:
                        signalBus.warning_Signal.emit(
                            f"删除远程配置失败: {result['message']}"
                        )
                else:
                    signalBus.warning_Signal.emit("无法从挂载配置中识别远程名称")
        else:
            signalBus.warning_Signal.emit("Rclone服务未运行，无法删除远程配置")

        # 删除UI卡片
        if card.name in self.mount_cards:
            # 立即从布局中移除widget
            self.scroll_layout.removeWidget(card)
            del self.mount_cards[card.name]
            card.deleteLater()
        self._update_empty_state()

    def add_mount_config(self):
        """
        添加挂载配置，首次使用时显示提示对话框
        """
        # 检查是否是首次点击添加挂载按钮
        if not cfg.get(cfg.firstMountTipShown):
            # 显示首次提示对话框
            tip_dialog = FirstMountTipDialog(self.window())
            
            if tip_dialog.exec():
                # 标记已显示过提示
                cfg.set(cfg.firstMountTipShown, True)
            else:
                # 用户取消，不继续添加挂载
                return
        
        # 显示添加挂载对话框
        dialog = AddMountDialog(None, self.window())
        if dialog.exec():
            new_config = dialog.get_mount_config()
            self.add_mount_card(new_config)
            current_configs = cfg.get(cfg.mountConfigs) or []
            current_configs.append(new_config)
            cfg.set(cfg.mountConfigs, current_configs)
            signalBus.success_Signal.emit(
                f"'{new_config['name']}' " + self.tr("已添加")
            )
            self._update_empty_state()

    def toggle_rclone_service(self):
        """
        切换Rclone服务状态（启动/停止）
        """
        if rcloneManager.is_core_running:
            signalBus.showLoadingSig.emit(self.tr("正在停止服务..."))
            rcloneManager.stop_core_service()
        else:
            signalBus.showLoadingSig.emit(self.tr("正在启动服务..."))
            rcloneManager.start_core_service()

    def show_rclone_version(self):
        """
        显示 Rclone 版本信息对话框
        """
        # 获取版本信息
        version_info = rcloneManager.get_rclone_version_info()
        if version_info:
            msg_box = MessageBox(self.tr("Rclone版本信息"), version_info, self.window())
            msg_box.yesButton.setText(self.tr("我知道了"))
            msg_box.cancelButton.hide()
            msg_box.exec()

    def show_rclone_logs(self):
        """
        显示Rclone日志查看对话框
        """
        if not rcloneManager.is_core_running:
            signalBus.warning_Signal.emit(
                self.tr("Rclone服务未运行，无法查看实时日志。")
            )
            return
            
        # 创建并显示日志对话框
        log_dialog = RcloneLogDialog(rcloneManager, self.window())
        log_dialog.exec()

    # --- rclone_manager 信号处理函数 ---
    def on_core_service_state_changed(self, is_running: bool, rc_url: str):
        """
        处理Rclone核心服务状态变化

        Args:
            is_running: 服务是否正在运行
            rc_url: 远程控制URL
        """
        # 隐藏全局加载动画
        signalBus.hideLoadingSig.emit()

        if is_running:
            self.start_button.setText(self.tr("停止服务"))
            self.start_button.setIcon(FIF.PAUSE)
            if not self.rclone_info_badge:
                self.rclone_info_badge = InfoBadge.success(
                    "运行中", self, self.mountTitleLabel, InfoBadgePosition.TOP_RIGHT
                )
                setFont(self.rclone_info_badge, 13)
                self.rclone_info_badge.adjustSize()
            self.rclone_info_badge.show()
        else:
            self.start_button.setText(self.tr("启动服务"))
            self.start_button.setIcon(FIF.PLAY)
            if self.rclone_info_badge:
                self.rclone_info_badge.hide()
            # 服务停止，所有卡片都应为未挂载状态
            for card in self.mount_cards.values():
                card.setMountedState(False)

    def on_mounts_info_updated(self, mounts_info: list):
        """处理来自 /mount/listmounts 的挂载信息更新"""
        # 挂载信息更新时隐藏全局加载动画
        signalBus.hideLoadingSig.emit()

        # API返回的是一个挂载点列表，我们需要将其与我们的配置进行匹配
        mounted_fs_paths = {info["Fs"] for info in mounts_info}

        for card in self.mount_cards.values():
            # 卡片配置中的 'fs' 字段 (e.g., "webdav:/Music")
            card_fs_path = card.getMountConfig().get("fs")

            # 处理路径格式差异：移除可能存在的前导斜杠进行匹配
            normalized_card_path = card_fs_path
            if card_fs_path and ":/" in card_fs_path:
                # 将 "webdav:/path" 转换为 "webdav:path" 进行匹配
                protocol, path = card_fs_path.split(":/", 1)
                normalized_card_path = f"{protocol}:{path}"

            # 检查两种格式是否匹配
            is_mounted = (
                card_fs_path in mounted_fs_paths
                or normalized_card_path in mounted_fs_paths
            )

            card.setMountedState(is_mounted)

    def on_log_message(self, message: str):
        """
        处理日志消息，安全地输出包含中文字符的内容
        
        Args:
            message: 日志消息字符串
        """
        try:
            print(f"[Rclone] {message}")
        except UnicodeEncodeError:
            # 如果遇到编码错误，使用安全的编码方式
            safe_message = message.encode('utf-8', errors='replace').decode('utf-8')
            print(f"[Rclone] {safe_message}")

    def on_error_occurred(self, error_message: str):
        signalBus.error_Signal.emit(f"Rclone错误: {error_message}")

    def on_settings_clicked(self, card: MountCard):
        mount_config = card.getMountConfig()
        dialog = AddMountDialog(mount_config, self.window())

        if dialog.exec():
            updated_config = dialog.get_mount_config()
            old_config = mount_config.copy()

            # 检查是否需要更新远程配置
            old_fs = old_config.get("fs", "")
            new_fs = updated_config.get("fs", "")

            # 从 fs 字段中提取远程名称
            old_remote_name = old_fs.split(":")[0] if ":" in old_fs else ""
            new_remote_name = new_fs.split(":")[0] if ":" in new_fs else ""

            # 如果是WebDAV配置且需要更新远程配置
            if (
                new_remote_name
                and new_remote_name.startswith("webdav")
                and rcloneManager.is_core_running
            ):
                # 获取WebDAV配置参数
                webdav_config = cfg.get(cfg.rcloneWebDavAccount) or {}
                if webdav_config.get("url") and webdav_config.get("user"):
                    # 准备更新远程配置的参数
                    remote_params = {
                        "url": webdav_config["url"],
                        "user": webdav_config["user"],
                        "pass": webdav_config.get("pass", ""),
                        "vendor": webdav_config.get("vendor", "other"),
                    }

                    # 使用TaskExecutor更新远程配置
                    def update_remote_task():
                        return rcloneManager.update_remote(
                            new_remote_name, "webdav", remote_params
                        )

                    def on_remote_update_completed(result):
                        if result.get("success"):
                            signalBus.success_Signal.emit(
                                f"远程配置 '{new_remote_name}' 已更新"
                            )
                        else:
                            signalBus.warning_Signal.emit(
                                f"更新远程配置失败: {result.get('message')}"
                            )

                    def on_remote_update_failed(future):
                        exception = future.getException()
                        error_msg = (
                            str(exception.exception)
                            if hasattr(exception, "exception")
                            else str(exception)
                        )
                        signalBus.error_Signal.emit(f"更新远程配置异常: {error_msg}")

                    # 提交更新任务
                    TaskExecutor.runTask(update_remote_task).then(
                        on_remote_update_completed, on_remote_update_failed
                    )

            # 更新本地卡片和配置
            # 在编辑模式下，卡片本身需要被替换，因为配置名称可能已更改
            old_card_name = mount_config.get("name")
            if old_card_name in self.mount_cards:
                del self.mount_cards[old_card_name]
                card.deleteLater()

            # 添加新的卡片
            self.add_mount_card(updated_config)

            # 更新配置文件
            current_configs = cfg.get(cfg.mountConfigs) or []
            old_name = mount_config.get("name")
            updated_configs = [
                updated_config if c.get("name") == old_name else c
                for c in current_configs
            ]
            cfg.set(cfg.mountConfigs, updated_configs)

            signalBus.success_Signal.emit(self.tr("挂载配置已更新"))

    def _execute_task(self, task_func, on_completed, on_failed):
        """通用任务执行器"""
        TaskExecutor.runTask(task_func).then(on_completed, on_failed)

    def on_start_clicked(self, card: MountCard):
        """
        处理挂载卡片的启动按钮点击事件

        Args:
            card: 被点击的挂载卡片
        """
        if not rcloneManager.is_core_running:
            signalBus.warning_Signal.emit(self.tr("请先启动 Rclone 服务"))
            return

        mount_config = card.getMountConfig()
        mount_point = card.getMountPoint()
        if not os.path.exists(mount_point):
            try:
                os.makedirs(mount_point, exist_ok=True)
            except OSError as e:
                signalBus.error_Signal.emit(f"创建挂载点失败: {e}")
                return

        # 显示全局加载动画
        signalBus.showLoadingSig.emit(f"正在启动挂载: {card.name}")

        def on_mount_completed(result):
            """挂载完成回调"""
            signalBus.hideLoadingSig.emit()
            if not result.get("success"):
                signalBus.warning_Signal.emit(f"挂载失败: {result.get('message')}")

        def on_mount_failed(future):
            """挂载失败回调"""
            signalBus.hideLoadingSig.emit()
            signalBus.error_Signal.emit(f"挂载操作异常: {future.getException()}")

        self._execute_task(
            lambda: rcloneManager.mount(mount_config),
            on_mount_completed,
            on_mount_failed,
        )

    def on_stop_clicked(self, card: MountCard):
        """
        处理挂载卡片的停止按钮点击事件

        Args:
            card: 被点击的挂载卡片
        """
        # 显示全局加载动画
        signalBus.showLoadingSig.emit(f"正在停止挂载: {card.name}")

        signalBus.success_Signal.emit(f"正在停止挂载: {card.name}")

        def on_unmount_completed(result):
            """卸载完成回调"""
            signalBus.hideLoadingSig.emit()
            if not result.get("success"):
                signalBus.warning_Signal.emit(f"卸载失败: {result.get('message')}")

        def on_unmount_failed(future):
            """卸载失败回调"""
            signalBus.hideLoadingSig.emit()
            signalBus.error_Signal.emit(f"卸载操作异常: {future.getException()}")

        self._execute_task(
            lambda: rcloneManager.unmount(card.getMountPoint()),
            on_unmount_completed,
            on_unmount_failed,
        )

    def _check_rclone_service_status(self):
        self.on_core_service_state_changed(
            rcloneManager.is_core_running, rcloneManager.rc_url or ""
        )
