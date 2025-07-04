# coding: utf-8
from PySide6.QtCore import QTimer
from qfluentwidgets import (
    BodyLabel,
    MessageBoxBase,
    PlainTextEdit,
    TitleLabel,
    setFont,
)


class RcloneLogDialog(MessageBoxBase):
    """Rclone日志查看对话框"""

    def __init__(self, rclone_manager, parent=None):
        """
        初始化Rclone日志查看对话框

        Args:
            rclone_manager: RcloneManager实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.rclone_manager = rclone_manager
        self.setupUI()
        self.load_logs()

        # 设置定时器自动刷新日志
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_logs)
        self.refresh_timer.start(1000)  # 每秒刷新一次

    def setupUI(self):
        """
        设置用户界面布局
        """
        # 设置对话框标题
        self.titleLabel = BodyLabel("Rclone 运行日志", self)
        setFont(self.titleLabel, 18)
        self.viewLayout.addWidget(self.titleLabel)

        # 创建日志显示区域
        self.logTextEdit = PlainTextEdit(self)
        self.logTextEdit.setReadOnly(True)
        self.logTextEdit.setMinimumSize(600, 400)
        self.logTextEdit.setMaximumHeight(500)

        # 设置等宽字体以便更好地显示日志，增大字体大小
        # font = self.logTextEdit.font()
        # font.setPointSize(12)  # 从9增大到12
        # self.logTextEdit.setFont(font)

        self.viewLayout.addWidget(self.logTextEdit)

        self.yesButton.setText("清空日志")
        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(self.clear_logs)

        self.cancelButton.setText("关闭")

    def load_logs(self):
        """
        加载并显示日志
        """
        logs = self.rclone_manager.get_log_messages()
        if logs:
            log_text = "\n".join(logs)
            self.logTextEdit.setPlainText(log_text)
            self.scroll_to_bottom()  # 默认滚动到底部
        else:
            self.logTextEdit.setPlainText("暂无日志信息")

    def refresh_logs(self):
        """
        刷新日志显示
        """
        current_text = self.logTextEdit.toPlainText()
        logs = self.rclone_manager.get_log_messages()
        new_text = "\n".join(logs) if logs else "暂无日志信息"

        # 只有当内容发生变化时才更新
        if current_text != new_text:
            self.logTextEdit.setPlainText(new_text)
            self.scroll_to_bottom()  # 默认滚动到底部

    def clear_logs(self):
        """
        清空日志
        """
        self.rclone_manager.clear_log_messages()
        self.logTextEdit.setPlainText("日志已清空")

    def scroll_to_bottom(self):
        """
        滚动到底部
        """
        scrollbar = self.logTextEdit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        """
        关闭事件处理
        """
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.stop()
        super().closeEvent(event)
