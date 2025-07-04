# coding:utf-8
"""
Author: Assistant
Date: 2024-12-19
Description: Loading dialog component based on MaskDialogBase
"""

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CaptionLabel,
    FluentStyleSheet,
    IndeterminateProgressRing,
    MaskDialogBase,
)


class LoadingDialog(MaskDialogBase):
    """加载动画对话框组件
    
    基于MaskDialogBase实现的loading加载动画组件，支持自定义文案、动画大小和自动隐藏功能。
    """

    def __init__(
        self,
        text: str = "加载中...",
        ring_size: int = 50,
        auto_hide_duration: Optional[int] = 5,
        parent: QWidget = None
    ):
        """
        初始化加载对话框
        
        Args:
            text: 加载文案，默认为"加载中..."
            ring_size: 进度环大小，默认为50像素
            auto_hide_duration: 自动隐藏时间（毫秒），None表示不自动隐藏
            parent: 父窗口
        """
        super().__init__(parent)
        self._text = text
        self._ring_size = ring_size
        self._auto_hide_duration = auto_hide_duration
        self._auto_hide_timer = None
        
        self._init_ui()
        self._update_widget_size()
        self._setup_auto_hide()
        
        FluentStyleSheet.DIALOG.apply(self.widget)

    def _init_ui(self):
        """
        初始化用户界面
        """
        # 为中心widget设置布局
        main_layout = QVBoxLayout(self.widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(10, 10, 10, 10)  # 设置合适的边距
        main_layout.setSpacing(20)  # 设置组件间距
        
        # 创建进度环
        self.progress_ring = IndeterminateProgressRing()
        self.progress_ring.setFixedSize(self._ring_size, self._ring_size)
        self.progress_ring.start()  # 开始动画
        
        # 创建文案标签
        self.text_label = CaptionLabel(self._text)
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 添加到布局
        main_layout.addWidget(self.progress_ring, 0, Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.setShadowEffect(60, (0, 6), QColor(0, 0, 0, 50))
        self.setMaskColor(QColor(0, 0, 0, 76))

    def _update_widget_size(self):
        """
        根据内容计算并设置widget的正方形尺寸
        取text的sizeHint()宽度和150的最小值
        """
        
        # 设置为正方形
        self.widget.setFixedSize(150, 150)
        
    def _setup_auto_hide(self):
        """
        设置自动隐藏定时器
        """
        if self._auto_hide_duration is not None:
            self._auto_hide_timer = QTimer()
            self._auto_hide_timer.setSingleShot(True)
            self._auto_hide_timer.timeout.connect(self.hide_loading)

    def show_loading(self):
        """
        显示加载对话框
        """
        self.progress_ring.start()
        if self._auto_hide_timer and self._auto_hide_duration:
            self._auto_hide_timer.start(self._auto_hide_duration)
        self.show()

    def hide_loading(self):
        """
        隐藏加载对话框
        """
        self.progress_ring.stop()
        if self._auto_hide_timer:
            self._auto_hide_timer.stop()
        self.hide()

    def set_text(self, text: str):
        """
        更新加载文案
        
        Args:
            text: 新的加载文案
        """
        self._text = text
        if hasattr(self, 'text_label'):
            self.text_label.setText(text)
            # 文案更新后重新计算尺寸
            self._update_widget_size()

    def set_ring_size(self, size: int):
        """
        更新进度环大小
        
        Args:
            size: 新的进度环大小（像素）
        """
        self._ring_size = size
        if hasattr(self, 'progress_ring'):
            self.progress_ring.setFixedSize(size, size)
            # 进度环尺寸更新后重新计算整体尺寸
            self._update_widget_size()

    def closeEvent(self, event):
        """
        关闭事件处理
        """
        self.hide_loading()
        super().closeEvent(event)