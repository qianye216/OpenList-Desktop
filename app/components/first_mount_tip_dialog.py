'''
Author: qianye
Date: 2025-07-04 10:02:58
LastEditTime: 2025-07-04 10:37:13
Description: 
'''

import platform

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    HyperlinkLabel,
    MessageBoxBase,
    StrongBodyLabel,
    setFont,
)


class FirstMountTipDialog(MessageBoxBase):
    """首次挂载提示对话框"""

    def __init__(self, parent=None):
        """
        初始化首次挂载提示对话框

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setupUI()

    def _get_system_info(self):
        """
        获取当前系统信息
        
        Returns:
            tuple: (系统类型, 是否为Windows, 是否为macOS)
        """
        system = platform.system().lower()
        is_windows = system == 'windows'
        is_macos = system == 'darwin'
        return system, is_windows, is_macos

    def _create_bullet_layout(self, text, url=None):
        """
        创建带项目符号的布局
        
        Args:
            text: 显示文本
            url: 可选的链接地址
            
        Returns:
            QHBoxLayout: 布局对象
        """
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 0, 0)  # 添加左边距
        bullet_label = BodyLabel("•", self)
        
        if url:
            link = HyperlinkLabel(text=text, parent=self)
            link.setUrl(url)
            layout.addWidget(bullet_label)
            layout.addWidget(link)
        else:
            text_label = BodyLabel(text, self)
            if text.startswith('$'):
                text_label.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                )
            layout.addWidget(bullet_label)
            layout.addWidget(text_label)
        
        layout.addStretch()
        return layout

    def setupUI(self):
        """
        设置用户界面布局
        """
        # 获取系统信息
        system, is_windows, is_macos = self._get_system_info()
        
        # 添加标题
        self.titleLabel = StrongBodyLabel(self.tr("先决条件"), self)
        setFont(self.titleLabel, 18, QFont.Weight.DemiBold)
        self.viewLayout.addWidget(self.titleLabel)

        # 创建内容布局
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)

        if is_windows:
            # Windows系统的安装指导
            desc_label = BodyLabel(self.tr("要在Windows系统上运行挂载，需要下载安装："), self)
            content_layout.addWidget(desc_label)

            # 添加WinFsp链接
            winfsp_layout = self._create_bullet_layout(
                "WinFsp - Windows File System Proxy",
                "https://winfsp.dev/rel/"
            )
            content_layout.addLayout(winfsp_layout)

            # 添加安装说明
            install_label = BodyLabel(self.tr("请从官网下载并安装WinFsp："), self)
            content_layout.addWidget(install_label)

            # 添加下载链接
            download_layout = self._create_bullet_layout(
                self.tr("WinFsp下载页面"),
                "https://winfsp.dev/rel/"
            )
            content_layout.addLayout(download_layout)

        elif is_macos:
            # macOS系统的安装指导
            desc_label = BodyLabel(self.tr("要在Mac系统上运行挂载，需要下载安装："), self)
            content_layout.addWidget(desc_label)

            # 添加FUSE for macOS链接
            fuse_layout = self._create_bullet_layout(
                "FUSE for macOS",
                "https://osxfuse.github.io/"
            )
            content_layout.addLayout(fuse_layout)

            # 添加安装命令说明
            install_label = BodyLabel(self.tr("您也可以使用以下命令安装："), self)
            content_layout.addWidget(install_label)

            # 添加命令文本
            command_layout = self._create_bullet_layout("$ brew install --cask macfuse")
            content_layout.addLayout(command_layout)

        else:
            # Linux或其他系统的安装指导
            desc_label = BodyLabel(self.tr("要在Linux系统上运行挂载，需要安装FUSE："), self)
            content_layout.addWidget(desc_label)

            # 添加安装命令
            ubuntu_layout = self._create_bullet_layout("$ sudo apt-get install fuse")
            content_layout.addLayout(ubuntu_layout)

            centos_layout = self._create_bullet_layout("$ sudo yum install fuse")
            content_layout.addLayout(centos_layout)

        # 添加参考链接
        ref_layout = QHBoxLayout()
        ref_label = BodyLabel(self.tr("参考："), self)
        ref_link = HyperlinkLabel(
            text="https://github.com/winfsp/cgofuse",
            parent=self
        )
        ref_link.setUrl("https://github.com/winfsp/cgofuse")
        ref_layout.addWidget(ref_label)
        ref_layout.addWidget(ref_link)
        ref_layout.addStretch()
        content_layout.addLayout(ref_layout)

        
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        self.viewLayout.addWidget(content_widget)

        # 设置按钮文本
        self.yesButton.setText(self.tr("我知道了"))

        # 设置对话框大小
        self.widget.setMinimumWidth(480)
        