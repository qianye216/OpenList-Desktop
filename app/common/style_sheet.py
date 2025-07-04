'''
Author: qianye
Date: 2025-06-08 20:32:52
LastEditTime: 2025-06-22 09:53:32
Description: 
'''


# coding: utf-8
from enum import Enum

from qfluentwidgets import StyleSheetBase, Theme, qconfig


class StyleSheet(StyleSheetBase, Enum):
    """Style sheet"""

    # TODO: Add your qss here

    SETTING_INTERFACE = "setting_interface"

    def path(self, theme=Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme
        return f":/app/qss/{theme.value.lower()}/{self.value}.qss"
