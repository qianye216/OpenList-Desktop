# coding:utf-8

from urllib.parse import urlparse

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    ConfigItem,
    ExpandGroupSettingCard,
    LineEdit,
    RadioButton,
)

from qfluentwidgets import FluentIcon as FIF
from ..common.config import cfg
from ..common.utils import getSystemProxy


class CustomProxySettingCard(ExpandGroupSettingCard):
    """自定义代理设置卡片组件"""

    def __init__(self, configItem: ConfigItem, parent=None):
        """
        初始化代理设置卡片
        
        Parameters
        ----------
        configItem: ConfigItem
            代理设置的配置项
        parent: QWidget
            父窗口组件
        """
        super().__init__(FIF.GLOBE, self.tr("代理"), self.tr("设置希望使用的代理"), parent=parent)
        self.configItem = configItem

        self._create_widgets()
        self._setup_layouts()
        self._connect_signals()
        self._set_initial_state()

    def _create_widgets(self):
        """创建所有子组件"""
        self.choiceLabel = BodyLabel(self.tr("自动检测系统代理"), self)

        # 单选按钮组
        self.radioWidget = QWidget(self.view)
        self.offRadioButton = RadioButton(self.tr("不使用代理"), self.radioWidget)
        self.defaultRadioButton = RadioButton(self.tr("自动检测系统代理"), self.radioWidget)
        self.customRadioButton = RadioButton(self.tr("使用自定义代理"), self.radioWidget)
        self.buttonGroup = QButtonGroup(self)
        self.buttonGroup.addButton(self.offRadioButton)
        self.buttonGroup.addButton(self.defaultRadioButton)
        self.buttonGroup.addButton(self.customRadioButton)

        # 自定义代理输入组件
        self.customProxyWidget = QWidget(self.view)
        self.customLabel = BodyLabel(self.tr("编辑代理服务器: "), self.customProxyWidget)
        self.customProtocolComboBox = ComboBox(self.customProxyWidget)
        self.customProtocolComboBox.addItems(["socks5", "http", "https"])
        self.label_1 = BodyLabel("://", self.customProxyWidget)
        self.customIPLineEdit = LineEdit(self.customProxyWidget)
        self.customIPLineEdit.setPlaceholderText(self.tr("代理 IP 地址"))
        self.label_2 = BodyLabel(":", self.customProxyWidget)
        self.customPortLineEdit = LineEdit(self.customProxyWidget)
        self.customPortLineEdit.setPlaceholderText(self.tr("端口"))

    def _setup_layouts(self):
        """配置和排列组件布局"""
        self.addWidget(self.choiceLabel)

        # 单选按钮布局
        radioLayout = QVBoxLayout(self.radioWidget)
        radioLayout.setSpacing(19)
        radioLayout.setAlignment(Qt.AlignTop)
        radioLayout.setContentsMargins(48, 18, 0, 18)
        radioLayout.addWidget(self.offRadioButton)
        radioLayout.addWidget(self.defaultRadioButton)
        radioLayout.addWidget(self.customRadioButton)

        # 自定义代理输入布局
        customProxyLayout = QHBoxLayout(self.customProxyWidget)
        customProxyLayout.setContentsMargins(48, 18, 44, 18)
        customProxyLayout.addWidget(self.customLabel)
        customProxyLayout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        customProxyLayout.addWidget(self.customProtocolComboBox)
        customProxyLayout.addWidget(self.label_1)
        customProxyLayout.addWidget(self.customIPLineEdit)
        customProxyLayout.addWidget(self.label_2)
        customProxyLayout.addWidget(self.customPortLineEdit)

        # 将子组件添加到主视图布局
        self.viewLayout.setSpacing(0)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.addGroupWidget(self.radioWidget)
        self.addGroupWidget(self.customProxyWidget)

    def _connect_signals(self):
        """连接组件信号到槽函数"""
        self.buttonGroup.buttonClicked.connect(self._on_radio_button_clicked)

        # 当用户完成编辑时保存自定义代理设置
        self.customProtocolComboBox.currentTextChanged.connect(self._on_custom_proxy_changed)
        self.customIPLineEdit.editingFinished.connect(self._on_custom_proxy_changed)
        self.customPortLineEdit.editingFinished.connect(self._on_custom_proxy_changed)

    def _set_initial_state(self):
        """根据当前配置设置初始UI状态"""
        value = self.configItem.value
        if value == "Auto":
            self.defaultRadioButton.setChecked(True)
        elif value == "Off":
            self.offRadioButton.setChecked(True)
        else:
            self.customRadioButton.setChecked(True)
            # 安全地解析并设置自定义代理字段
            parsed_proxy = self._parse_proxy_string(value)
            if parsed_proxy:
                self.customProtocolComboBox.setCurrentText(parsed_proxy.scheme)
                self.customIPLineEdit.setText(parsed_proxy.hostname)
                self.customPortLineEdit.setText(str(parsed_proxy.port))

        # 根据选中的按钮更新UI
        self._update_ui_for_mode(self.buttonGroup.checkedButton())

    def _update_ui_for_mode(self, button: RadioButton):
        """根据选择的模式更新UI元素，如标签和组件状态"""
        if not button:
            return

        self.choiceLabel.setText(button.text())
        self.choiceLabel.adjustSize()

        # 判断是否为自定义模式
        is_custom_mode = (button is self.customRadioButton)
        self.customProxyWidget.setEnabled(is_custom_mode)

        if button is self.defaultRadioButton:
            # 自动检测并填充系统代理，但不保存为自定义设置
            sys_proxy = getSystemProxy()
            if sys_proxy and (parsed_proxy := self._parse_proxy_string(sys_proxy)):
                self.customProtocolComboBox.setCurrentText(parsed_proxy.scheme)
                self.customIPLineEdit.setText(parsed_proxy.hostname)
                self.customPortLineEdit.setText(str(parsed_proxy.port))
            else:
                self.customProtocolComboBox.setCurrentText(self.customProtocolComboBox.itemText(0))
                self.customIPLineEdit.setText(self.tr("未检测到代理"))
                self.customPortLineEdit.clear()

    @Slot(RadioButton)
    def _on_radio_button_clicked(self, button: RadioButton):
        """处理单选按钮点击事件以切换代理模式"""
        self._update_ui_for_mode(button)

        if button is self.defaultRadioButton:
            cfg.set(self.configItem, "Auto")
        elif button is self.offRadioButton:
            cfg.set(self.configItem, "Off")
        elif button is self.customRadioButton:
            # 切换到自定义模式时，立即尝试保存当前字段的状态
            self._on_custom_proxy_changed()

    @Slot()
    def _on_custom_proxy_changed(self):
        """验证并保存自定义代理配置"""
        # 只有在自定义模式激活时才执行此槽函数
        if not self.customRadioButton.isChecked():
            return

        proxy_server_str = self._build_proxy_string()
        if self._is_valid_proxy_format(proxy_server_str):
            cfg.set(self.configItem, proxy_server_str)
        else:
            # 可选：提供格式无效的反馈
            # 在此示例中，我们保持原有逻辑，如果用户将字段留在无效状态则恢复为默认值
            # 更好的用户体验可能是显示视觉错误提示（例如红色边框）
            pass  # 或在此处理无效输入反馈

    def _build_proxy_string(self) -> str:
        """从UI字段构建代理服务器字符串"""
        protocol = self.customProtocolComboBox.currentText()
        ip = self.customIPLineEdit.text().strip()
        port = self.customPortLineEdit.text().strip()
        return f"{protocol}://{ip}:{port}"

    def _is_valid_proxy_format(self, proxy_string: str) -> bool:
        """检查代理字符串是否符合所需格式"""
        # 使用原始代码中的正则表达式进行验证
        return bool(cfg.proxyServer.validator.PATTERN.match(proxy_string))

    def _parse_proxy_string(self, proxy_string: str):
        """安全地解析代理URL字符串，失败时返回None"""
        try:
            # 如果缺少协议头，为urlparse添加协议头以正确工作，尽管我们的格式要求包含协议头
            if "://" not in proxy_string:
                return None
            parsed = urlparse(proxy_string)
            if parsed.scheme and parsed.hostname and parsed.port:
                return parsed
        except (ValueError, AttributeError):
            pass
        return None
