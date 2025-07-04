import platform

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget
from qfluentwidgets import (
    ExpandLayout,
    HyperlinkCard,
    PrimaryPushSettingCard,
    SettingCardGroup,
)
from qfluentwidgets import FluentIcon as FIF

from ..common.setting import APP_NAME, AUTHOR, FEEDBACK_URL, HELP_URL, VERSION, YEAR
from ..common.signal_bus import signalBus


class AboutInterface(QWidget):
    """Setting interface"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.platform_name = platform.system()

        self._initWidget()
        self._initLayout()
        self._connectSignalToSlot()

    def _initWidget(self):
        self.setObjectName("AboutInterface")

        self.expandLayout = ExpandLayout(self)

        self.aboutGroup = SettingCardGroup(self.tr("关于"), self)

        self.helptutorialCard = HyperlinkCard(
            HELP_URL,
            self.tr("打开帮助页面"),
            FIF.HELP,
            self.tr("帮助"),
            self.tr("发现新功能并了解有关") + f"{APP_NAME}" + self.tr("的使用技巧"),
            self.aboutGroup,
        )
        self.feedbackCard = PrimaryPushSettingCard(
            self.tr("提供反馈"),
            FIF.FEEDBACK,
            self.tr("提供反馈"),
            self.tr("通过提供反馈帮助我们改进") + f"{APP_NAME}",
            self.aboutGroup,
        )

        self.checkversionCard = PrimaryPushSettingCard(
            self.tr("检查更新"),
            FIF.UPDATE,
            self.tr("关于"),
            "© "
            + self.tr("版权所有")
            + f" {YEAR}, {AUTHOR}. "
            + self.tr("当前版本")
            + " "
            + VERSION,
            self.aboutGroup,
        )

    def _initLayout(self):
        self.aboutGroup.addSettingCard(self.helptutorialCard)
        self.aboutGroup.addSettingCard(self.feedbackCard)
        self.aboutGroup.addSettingCard(self.checkversionCard)

        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(16, 10, 16, 10)
        self.expandLayout.addWidget(self.aboutGroup)

    def _connectSignalToSlot(self):
        self.feedbackCard.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(FEEDBACK_URL))
        )
        self.checkversionCard.clicked.connect(signalBus.checkUpdateSig)
