"""
Author: qianye
Date: 2025-06-25 09:11:59
LastEditTime: 2025-06-29 17:24:23
Description:
"""

# coding:utf-8
import textwrap

import markdown2
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
)
from qfluentwidgets import (
    BodyLabel,
    MessageBoxBase,
    ScrollArea,
    TitleLabel,
)


class MarkDownMessageBox(MessageBoxBase):
    """可滚动的消息对话框"""

    def __init__(self, title, content, parent=None):
        """
        初始化可滚动消息对话框

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.title = title
        self.content = content
        self.setupUI()

    def setupUI(self):
        """
        设置用户界面布局
        """
        # 添加标题
        self.titleLabel = TitleLabel(self.title, self)
        self.viewLayout.addWidget(self.titleLabel)

        self.contentLabel = BodyLabel(self)
        markdown_text = textwrap.dedent(self.content)
        markdown_content = markdown2.markdown(markdown_text)
        self.contentLabel.setText(markdown_content)
        self.contentLabel.setWordWrap(True)
        # 合并文本交互标志，同时支持链接点击和文本浏览
        self.contentLabel.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse | 
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.contentLabel.setOpenExternalLinks(True)
        self.contentLabel.linkActivated.connect(
            lambda url: QDesktopServices.openUrl(QUrl(url))
        )

        self.scrollArea = ScrollArea()
        self.scrollArea.enableTransparentBackground()
        self.scrollArea.setWidget(self.contentLabel)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setMaximumHeight(480)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scrollArea.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        

        self.viewLayout.addWidget(self.scrollArea)

        # 设置按钮文本
        self.yesButton.setText(self.tr("确定"))
        self.cancelButton.setText(self.tr("取消"))

    def setContentCopyable(self, isCopyable: bool):
        if isCopyable:
            self.contentLabel.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
        else:
            self.contentLabel.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction
            )
