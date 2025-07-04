from typing import Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from qfluentwidgets import (
    FluentIconBase,
    InfoBar,
    InfoBarIcon,
    InfoBarPosition,
)

class MyInfoBar(InfoBar):
    def __init__(
        self,
        icon: Union[InfoBarIcon, FluentIconBase, QIcon, str],
        title: str,
        content: str,
        orient=Qt.Horizontal,
        isClosable=True,
        duration=2000,
        position=InfoBarPosition.TOP,
        parent=None,
    ):
        super().__init__(parent=parent)

    @classmethod
    def info(
        cls,
        title,
        content,
        orient=Qt.Horizontal,
        isClosable=False,
        duration=2000,
        position=InfoBarPosition.TOP,
        parent=None,
    ):
        return cls.new(
            InfoBarIcon.INFORMATION,
            title,
            content,
            orient,
            isClosable,
            duration,
            position,
            parent,
        )

    @classmethod
    def success(
        cls,
        title,
        content,
        orient=Qt.Horizontal,
        isClosable=False,
        duration=2000,
        position=InfoBarPosition.TOP,
        parent=None,
    ):
        return cls.new(
            InfoBarIcon.SUCCESS,
            title,
            content,
            orient,
            isClosable,
            duration,
            position,
            parent,
        )

    @classmethod
    def warning(
        cls,
        title,
        content,
        orient=Qt.Horizontal,
        isClosable=False,
        duration=2000,
        position=InfoBarPosition.TOP,
        parent=None,
    ):
        return cls.new(
            InfoBarIcon.WARNING,
            title,
            content,
            orient,
            isClosable,
            duration,
            position,
            parent,
        )

    @classmethod
    def error(
        cls,
        title,
        content,
        orient=Qt.Horizontal,
        isClosable=False,
        duration=2000,
        position=InfoBarPosition.TOP,
        parent=None,
    ):
        return cls.new(
            InfoBarIcon.ERROR,
            title,
            content,
            orient,
            isClosable,
            duration,
            position,
            parent,
        )