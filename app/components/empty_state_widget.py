# coding:utf-8

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    IconWidget,
    StrongBodyLabel,
    setFont,
)


class EmptyStateWidget(QWidget):
    """空状态组件，用于显示缺省图标和文案"""

    def __init__(self, 
                 icon=None, 
                 title="暂无数据",
                 description="",
                 parent=None):
        super().__init__(parent=parent)
        
        self.icon = icon
        self.title = title
        self.description = description
        
        self._initWidget()
        self._initLayout()
    
    def _initWidget(self):
        """初始化组件"""
        # 图标（只有在提供图标时才创建）
        self.iconWidget = None
        if self.icon is not None:
            self.iconWidget = IconWidget(self.icon)
            self.iconWidget.setFixedSize(80, 80)
            self.iconWidget.setStyleSheet("color: rgba(0, 0, 0, 0.3);")
        
        # 标题
        self.titleLabel = StrongBodyLabel(self.title)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        setFont(self.titleLabel, 16)
        
        # 描述文字
        self.descriptionLabel = BodyLabel(self.description)
        self.descriptionLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.descriptionLabel.setWordWrap(True)
        
        # 设置样式
        self.titleLabel.setStyleSheet("color: rgba(0, 0, 0, 0.6);")
        self.descriptionLabel.setStyleSheet("color: rgba(0, 0, 0, 0.4);")
        
        # 设置最小高度确保不重叠
        self.titleLabel.setMinimumHeight(24)
        self.descriptionLabel.setMinimumHeight(48)
    
    def _initLayout(self):
        """初始化布局"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)  # 增加间距
        # 减少上下边距，避免在受限容器中被截断
        layout.setContentsMargins(40, 60, 40, 30)  # 从60减少到30
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 只有在图标存在时才添加图标
        if self.iconWidget is not None:
            layout.addWidget(self.iconWidget, 0, Qt.AlignmentFlag.AlignCenter)
            # 添加一些额外间距
            layout.addSpacing(10)
        
        # 添加标题
        layout.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 如果有描述文字，添加描述
        if self.description:
            # 给 descriptionLabel 设置拉伸因子为1，允许它根据内容扩展
            layout.addWidget(self.descriptionLabel, 1, Qt.AlignmentFlag.AlignCenter)
    
    def setIcon(self, icon):
        """设置图标"""
        self.icon = icon
        
        # 如果之前没有图标组件，需要创建
        if icon is not None and self.iconWidget is None:
            self.iconWidget = IconWidget(icon)
            self.iconWidget.setFixedSize(80, 80)
            self.iconWidget.setStyleSheet("color: rgba(0, 0, 0, 0.3);")
            # 将图标插入到布局的最前面
            layout = self.layout()
            layout.insertWidget(0, self.iconWidget)
            layout.insertSpacing(1, 10)  # 在图标后添加间距
        elif icon is not None and self.iconWidget is not None:
            # 更新现有图标
            self.iconWidget.setIcon(icon)
        elif icon is None and self.iconWidget is not None:
            # 移除图标
            self.iconWidget.setParent(None)
            self.iconWidget.deleteLater()
            self.iconWidget = None
    
    def setTitle(self, title):
        """设置标题"""
        self.title = title
        self.titleLabel.setText(title)
    
    def setDescription(self, description):
        """设置描述"""
        self.description = description
        self.descriptionLabel.setText(description)
        self.descriptionLabel.setVisible(bool(description))
