'''
Author: qianye
Date: 2025-06-08 20:32:52
LastEditTime: 2025-07-01 15:57:55
Description: 
'''
# coding:utf-8
import os
import sys

from PySide6.QtCore import Qt, QTranslator
from qfluentwidgets import FluentTranslator

from app.common.application import SingletonApplication
from app.common.config import cfg
from app.view.main_window import MainWindow

# enable dpi scale
if cfg.get(cfg.dpiScale) != "Auto":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

# create application
app = SingletonApplication(sys.argv,"OpenList-Desktop")
app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
app.setQuitOnLastWindowClosed(False)

# internationalization
locale = cfg.get(cfg.language).value
translator = FluentTranslator(locale)
galleryTranslator = QTranslator()
galleryTranslator.load(locale, "app", ".", ":/app/i18n")

app.installTranslator(translator)
app.installTranslator(galleryTranslator)

# create main window
w = MainWindow()
if not cfg.quietAutoStartUp.value:
    w.show()

app.exec()
