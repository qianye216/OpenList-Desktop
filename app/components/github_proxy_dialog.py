# coding:utf-8
"""
Author: qianye
Date: 2025-07-02
Description: A dialog for setting the GitHub proxy.
"""

from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    LineEdit,
    MessageBoxBase,
    setFont,
)


class GitHubProxyDialog(MessageBoxBase):
    """GitHub 代理设置对话框"""

    def __init__(self, current_proxy="", parent=None):
        """
        初始化GitHub代理对话框

        Args:
            current_proxy (str): 当前的代理地址
            parent: 父窗口
        """
        super().__init__(parent)
        self.current_proxy = current_proxy
        self.setupUI()

    def setupUI(self):
        """
        设置用户界面布局
        """
        # 添加标题
        self.titleLabel = BodyLabel(self.tr("设置GitHub代理"), self)
        setFont(self.titleLabel, 18)
        self.viewLayout.addWidget(self.titleLabel)

        # 添加说明文本
        self.descLabel = BodyLabel(
            self.tr(
                "请输入您的GitHub代理地址，例如：https://ghproxy.com/"
            ),
            self,
        )
        self.notesLabel = CaptionLabel(
            self.tr(
                "注意：代理地址将用于加速GitHub相关内容的下载。"
            ),
            self,
        )
        self.descLabel.setWordWrap(True)
        self.viewLayout.addWidget(self.descLabel)
        self.viewLayout.addWidget(self.notesLabel)

        # 创建代理输入框
        self.proxyLineEdit = LineEdit(self)
        self.proxyLineEdit.setPlaceholderText(
            self.tr("输入GitHub代理地址")
        )
        self.proxyLineEdit.setClearButtonEnabled(True)

        # 设置当前代理值
        if self.current_proxy:
            self.proxyLineEdit.setText(self.current_proxy)

        # 添加到布局
        self.viewLayout.addWidget(self.proxyLineEdit)

        # 设置按钮文本
        self.yesButton.setText(self.tr("确定"))
        self.cancelButton.setText(self.tr("取消"))

        # 设置对话框最小宽度
        self.widget.setMinimumWidth(450)

    def getProxy(self):
        """
        获取输入的代理地址

        Returns:
            str: 输入的代理地址
        """
        return self.proxyLineEdit.text().strip()
