'''
Author: qianye
Date: 2025-06-25 09:17:08
LastEditTime: 2025-07-02 09:01:26
Description: 
'''


from PySide6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
)
from qfluentwidgets import (
    Action,
    SystemTrayMenu,
)

from ..common.signal_bus import signalBus


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setIcon(parent.windowIcon())

        self.menu = SystemTrayMenu(parent=parent)
        self.menu.addActions(
            [
                Action(
                    self.tr("显示主窗口"),
                    triggered=lambda: signalBus.appMessageSig.emit("show"),
                ),
                Action(
                    self.tr("隐藏"),
                    triggered=lambda: signalBus.appMessageSig.emit("hide"),
                ),
                Action(self.tr("退出"), triggered=QApplication.instance().quit),
            ]
        )
        self.setContextMenu(self.menu)
