# coding:utf-8

from qfluentwidgets import (
    BodyLabel,
    MessageBoxBase,
    PasswordLineEdit,
    setFont,
)

class AdminInfoDialog(MessageBoxBase):
    """管理员信息对话框"""

    def __init__(self, parent=None):
        """
        初始化管理员信息对话框

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        """
        设置用户界面布局
        """

        # 添加标题
        self.titleLabel = BodyLabel(self.tr("管理员信息"), self)
        setFont(self.titleLabel, 18)
        self.viewLayout.addWidget(self.titleLabel)

        # 创建新密码输入框
        self.passwordLineEdit = PasswordLineEdit()
        self.passwordLineEdit.setPlaceholderText(self.tr("保持为空以设置随机密码"))
        self.passwordLineEdit.setClearButtonEnabled(True)

        # 连接文本变化信号
        self.passwordLineEdit.textChanged.connect(self._onPasswordTextChanged)

        # 添加到布局
        self.viewLayout.addWidget(self.passwordLineEdit)

        # 设置按钮文本
        self.yesButton.setText(self.tr("随机新密码"))
        self.cancelButton.setText(self.tr("取消"))

        # 设置对话框最小宽度
        self.widget.setMinimumWidth(400)

    def _onPasswordTextChanged(self, text):
        """
        当密码输入框文本变化时的处理函数

        Args:
            text: 输入框中的文本
        """
        if text.strip():  # 如果输入框不为空
            self.yesButton.setText(self.tr("设置新密码"))
        else:  # 如果输入框为空
            self.yesButton.setText(self.tr("随机新密码"))

    def getPassword(self):
        """
        获取输入的密码

        Returns:
            str: 输入的密码
        """
        return self.passwordLineEdit.text().strip()
