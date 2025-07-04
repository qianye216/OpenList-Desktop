"""
Author: qianye
Date: 2025-06-30 10:04:34
LastEditTime: 2025-06-30 10:14:11
Description:
"""
# coding:utf-8

from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    MessageBoxBase,
    PasswordLineEdit,
    setFont,
)


class GitHubTokenDialog(MessageBoxBase):
    """GitHub访问令牌对话框"""

    def __init__(self, current_token="", parent=None):
        """
        初始化GitHub访问令牌对话框

        Args:
            current_token (str): 当前的令牌值
            parent: 父窗口
        """
        super().__init__(parent)
        self.current_token = current_token
        self.setupUI()

    def setupUI(self):
        """
        设置用户界面布局
        """
        # 添加标题
        self.titleLabel = BodyLabel(self.tr("设置GitHub访问令牌"), self)
        setFont(self.titleLabel, 18)
        self.viewLayout.addWidget(self.titleLabel)

        # 添加说明文本
        self.descLabel = BodyLabel(
            self.tr(
                "请输入您的GitHub Personal Access Token (<a href='https://github.com/settings/personal-access-tokens'>前往设置</a>):"
            ),
            self,
        )
        self.notesLabel = CaptionLabel(
            self.tr(
                "注意：访问令牌仅用于访问GitHub API，提升接口请求频率，不会上传任何数据。"
            ),
            self,
        )
        self.descLabel.setWordWrap(True)
        self.descLabel.setOpenExternalLinks(True)  # 启用外部链接打开
        self.viewLayout.addWidget(self.descLabel)
        self.viewLayout.addWidget(self.notesLabel)

        # 创建令牌输入框
        self.tokenLineEdit = PasswordLineEdit()
        self.tokenLineEdit.setPlaceholderText(
            self.tr("输入GitHub Personal Access Token")
        )
        self.tokenLineEdit.setClearButtonEnabled(True)

        # 设置当前令牌值
        if self.current_token:
            self.tokenLineEdit.setText(self.current_token)

        # 连接文本变化信号
        self.tokenLineEdit.textChanged.connect(self._onTokenTextChanged)

        # 添加到布局
        self.viewLayout.addWidget(self.tokenLineEdit)

        # 设置按钮文本
        self.yesButton.setText(self.tr("确定"))
        self.cancelButton.setText(self.tr("取消"))

        # 设置对话框最小宽度
        self.widget.setMinimumWidth(450)

    def _onTokenTextChanged(self, text):
        """
        当令牌输入框文本变化时的处理函数

        Args:
            text (str): 输入框中的文本
        """
        # 可以在这里添加实时验证逻辑
        pass

    def getToken(self):
        """
        获取输入的令牌

        Returns:
            str: 输入的令牌
        """
        return self.tokenLineEdit.text().strip()
