'''
Author: qianye
Date: 2025-06-08 20:32:52
LastEditTime: 2025-06-29 10:54:03
Description: 
'''


# coding: utf-8
from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    """Signal bus"""
    
    appMessageSig = Signal(str)
    appErrorSig = Signal(str)

    checkUpdateSig = Signal()
    micaEnableChanged = Signal(bool)

    # 传递信息
    success_Signal = Signal((str,),(str, str))
    warning_Signal = Signal((str,), (str,str))
    error_Signal = Signal((str,),(str, str))

    trace_Signal = Signal(str)
    
    # 新增：加载动画控制信号
    showLoadingSig = Signal(str)  # 显示加载动画，参数为加载文案
    hideLoadingSig = Signal()    # 隐藏加载动画
    updateLoadingTextSig = Signal(str)  # 更新加载文案


signalBus = SignalBus()
