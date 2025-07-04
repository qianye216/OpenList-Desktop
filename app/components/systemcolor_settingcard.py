"""
Author: qianye
Date: 2025-06-22 15:13:18
LastEditTime: 2025-06-27 13:48:38
Description: 优化的系统主题色设置卡片，支持跟随系统设置并修复相关问题
"""

# coding:utf-8
from typing import Union

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
)
from qfluentwidgets import (
    ColorConfigItem,
    CustomColorSettingCard,
    FluentIconBase,
    RadioButton,
    qconfig,
    setThemeColor,
)

from ..common.config import cfg

# 导入获取系统主题色的函数
try:
    from qframelesswindow.utils import getSystemAccentColor
except ImportError:
    def getSystemAccentColor():
        """Fallback function for systems where getSystemAccentColor is not available"""
        return QColor(Qt.transparent)


class SystemColorSettingCard(CustomColorSettingCard):
    """
    一个增加了"跟随系统设置"选项的主题颜色设置卡。
    """
    
    # 特殊标识符，用于标记"跟随系统设置"状态
    FOLLOW_SYSTEM_FLAG = "#FOLLOW_SYSTEM#"

    def __init__(
        self,
        configItem: ColorConfigItem,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content=None,
        parent=None,
        enableAlpha=False,
    ):
        """
        参数:
        ----------
        configItem: ColorConfigItem
            配置项

        icon: str | QIcon | FluentIconBase
            图标

        title: str
            设置卡标题

        content: str
            设置卡内容

        parent: QWidget
            父窗口

        enableAlpha: bool
            是否启用 alpha 通道
        """
        # 获取系统颜色，用于后续比较
        try:
            self.systemColor = getSystemAccentColor()
        except Exception:
            # 在非macOS系统上，此函数可能会失败，提供一个回退
            self.systemColor = QColor(Qt.transparent)

        # 调用父类的构造函数
        super().__init__(configItem, icon, title, content, parent, enableAlpha)

        self.setObjectName("SystemColorSettingCard")

        # --- 添加新组件和修正逻辑 ---

        # 1. 创建新的 RadioButton
        self.systemRadioButton = RadioButton(self.tr("跟随系统设置"), self.radioWidget)

        # 2. 将其添加到 ButtonGroup 和布局中
        self.buttonGroup.addButton(self.systemRadioButton)
        self.radioLayout.insertWidget(0, self.systemRadioButton)

        # 3. 【关键修复】断开父类建立的连接，然后重新连接到子类的方法
        # 这是为了确保点击任何按钮时，都会调用我们重写的 __onRadioButtonClicked
        self.buttonGroup.buttonClicked.disconnect()
        self.buttonGroup.buttonClicked.connect(self.__onRadioButtonClicked)

        self.radioLayout.setSizeConstraint(QVBoxLayout.SetDefaultConstraint)
        self.customColorLayout.setSizeConstraint(QHBoxLayout.SetDefaultConstraint)
        # 在添加了新的RadioButton后，必须重新计算可展开区域的高度。
        self._adjustViewSize()

        # 4. 重置初始状态以正确反映 "Follow system" 选项
        self.__resetInitialState()
        
        # 5. 设置定时器监听系统颜色变化
        self.systemColorTimer = QTimer(self)
        self.systemColorTimer.timeout.connect(self.updateSystemColor)
        # 每5秒检查一次系统颜色是否改变
        self.systemColorTimer.start(5000)
        
        # 启动时立即检查一次系统颜色状态
        QTimer.singleShot(100, self.__syncColorOnStartup)

    def __resetInitialState(self):
        """根据当前配置的颜色，设置正确的初始单选按钮状态"""
        # 检查是否启用了跟随系统设置
        follow_system = cfg.get(cfg.followSystemThemeColor)
        
        if follow_system and self.systemColor.isValid():
            # 如果启用了跟随系统设置，则选中系统颜色选项并更新颜色
            self.systemRadioButton.setChecked(True)
            self.chooseColorButton.setEnabled(False)
            # 确保配置中的颜色是最新的系统颜色
            qconfig.set(self.configItem, self.systemColor)
        else:
            savedColor = QColor(qconfig.get(self.configItem))
            if savedColor == self.defaultColor:
                self.defaultRadioButton.setChecked(True)
                self.chooseColorButton.setEnabled(False)
            else:
                self.customRadioButton.setChecked(True)
                self.chooseColorButton.setEnabled(True)

        checked_button = self.buttonGroup.checkedButton()
        if checked_button:
            self.choiceLabel.setText(checked_button.text())
            self.choiceLabel.adjustSize()

        # 如果没有有效的系统颜色（例如在Windows/Linux上），禁用该选项
        if not self.systemColor.isValid():
            self.systemRadioButton.setDisabled(True)
            self.systemRadioButton.setText(self.tr("跟随系统设置 (不可用)"))

    def __onRadioButtonClicked(self, button: RadioButton):
        """重写 radio button 点击槽函数，以处理所有三种情况"""
        # 如果点击的是当前已选中的按钮，则不执行任何操作
        if button.text() == self.choiceLabel.text():
            return

        self.choiceLabel.setText(button.text())
        self.choiceLabel.adjustSize()

        color_to_set = None

        if button is self.systemRadioButton:
            self.chooseColorButton.setDisabled(True)
            # 重新获取以防系统设置发生变化
            self.systemColor = getSystemAccentColor()
            color_to_set = self.systemColor
            # 设置跟随系统设置标志
            cfg.set(cfg.followSystemThemeColor, True)
        elif button is self.defaultRadioButton:
            self.chooseColorButton.setDisabled(True)
            color_to_set = self.defaultColor
            # 取消跟随系统设置标志
            cfg.set(cfg.followSystemThemeColor, False)
        elif button is self.customRadioButton:
            self.chooseColorButton.setDisabled(False)
            # 使用已保存的自定义颜色。如果用户想更改，他们会点击“选择颜色”按钮。
            color_to_set = self.customColor
            # 取消跟随系统设置标志
            cfg.set(cfg.followSystemThemeColor, False)

        if color_to_set:
            current_color = QColor(qconfig.get(self.configItem))
            if current_color != color_to_set:
                qconfig.set(self.configItem, color_to_set)
                self.colorChanged.emit(color_to_set)

    def __onCustomColorChanged(self, color: QColor):
        """
        当自定义颜色改变时，确保自定义单选按钮被选中。
        """
        # 调用父类方法来保存颜色和发出信号
        super().__onCustomColorChanged(color)
        
        # 取消跟随系统设置标志
        cfg.set(cfg.followSystemThemeColor, False)

        # 确保 "Custom color" 选项在UI上被选中
        if not self.customRadioButton.isChecked():
            self.customRadioButton.setChecked(True)
            # 手动触发一次点击逻辑，以更新标签文本
            self.__onRadioButtonClicked(self.customRadioButton)
    
    def updateSystemColor(self):
        """
        更新系统主题色，当检测到系统主题色改变时调用
        """
        try:
            new_system_color = getSystemAccentColor()
            if new_system_color.isValid() and new_system_color != self.systemColor:
                self.systemColor = new_system_color
                
                # 检查是否启用了跟随系统设置
                follow_system = cfg.get(cfg.followSystemThemeColor)
                
                if follow_system:
                    # 如果启用了跟随系统设置，则更新颜色并强制刷新主题
                    qconfig.set(self.configItem, self.systemColor)
                    # 强制触发主题色更新，确保所有组件都收到更新
                    setThemeColor(self.systemColor)
                    self.colorChanged.emit(self.systemColor)
        except Exception:
            # 处理获取系统颜色失败的情况
            pass
    
    def getValue(self):
        """
        获取当前设置的颜色值
        """
        return QColor(qconfig.get(self.configItem))
    
    def setValue(self, color: QColor):
        """
        设置颜色值并更新UI状态
        """
        if not isinstance(color, QColor) or not color.isValid():
            return
            
        qconfig.set(self.configItem, color)
        
        # 更新UI状态
        if self.systemColor.isValid() and color.rgb() == self.systemColor.rgb():
            self.systemRadioButton.setChecked(True)
            self.choiceLabel.setText(self.systemRadioButton.text())
            self.chooseColorButton.setEnabled(False)
        elif color == self.defaultColor:
            self.defaultRadioButton.setChecked(True)
            self.choiceLabel.setText(self.defaultRadioButton.text())
            self.chooseColorButton.setEnabled(False)
        else:
            self.customRadioButton.setChecked(True)
            self.choiceLabel.setText(self.customRadioButton.text())
            self.chooseColorButton.setEnabled(True)
            
        self.choiceLabel.adjustSize()
        self.colorChanged.emit(color)
    
    def __syncColorOnStartup(self):
        """
        应用启动时同步颜色状态，修复"跟随系统设置"选项在系统颜色变化后启动时显示为自定义颜色的问题
        """
        try:
            # 重新获取最新的系统颜色
            current_system_color = getSystemAccentColor()
            if current_system_color.isValid():
                self.systemColor = current_system_color
                
                # 检查是否启用了跟随系统设置
                follow_system = cfg.get(cfg.followSystemThemeColor)
                
                if follow_system:
                    # 如果启用了跟随系统设置，确保使用最新的系统颜色
                    saved_color = QColor(qconfig.get(self.configItem))
                    if saved_color.rgb() != current_system_color.rgb():
                        qconfig.set(self.configItem, current_system_color)
                        # 在启动时也要强制更新主题色，确保所有组件都使用正确的颜色
                        setThemeColor(current_system_color)
                        self.colorChanged.emit(current_system_color)
                        
        except Exception:
            # 处理任何可能的异常
            pass
