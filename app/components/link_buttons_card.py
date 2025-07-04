'''
Author: qianye
Date: 2025-06-26 08:28:05
LastEditTime: 2025-07-03 22:02:05
Description: 
'''
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout

from qfluentwidgets import (
    CardWidget,
    TransparentPushButton,
    FluentIcon as FIF,
)

from ..common.setting import DOC_URL, GITHUB_URL, SUPPORT_URL


class LinkButtonsCard(CardWidget):
    """链接按钮卡片组件，包含文档、GitHub和赞助按钮"""

    def __init__(self, parent=None):
        """
        初始化链接按钮卡片组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self.setObjectName("LinkButtonsCard")
        
        self._initWidget()
        self._initLayout()
        self._connectSignalToSlot()

    def _initWidget(self):
        """初始化组件"""
        # 创建三个链接按钮
        self.help_doc_button = TransparentPushButton(self.tr("帮助文档"), self)
        self.help_doc_button.setIcon(FIF.HELP)

        self.github_button = TransparentPushButton(self.tr("GitHub"), self)
        self.github_button.setIcon(FIF.GITHUB)

        self.support_button = TransparentPushButton(self.tr("赞助作者"), self)
        self.support_button.setIcon(FIF.HEART)

    def _initLayout(self):
        """初始化布局"""
        # 创建水平布局
        layout = QHBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.help_doc_button)
        layout.addWidget(self.github_button)
        layout.addWidget(self.support_button)
        layout.addStretch()
        
        # 设置布局边距和间距
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

    def _connectSignalToSlot(self):
        """连接信号到槽函数"""
        self.help_doc_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(DOC_URL))
        )
        self.github_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL))
        )
        self.support_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(SUPPORT_URL))
        )