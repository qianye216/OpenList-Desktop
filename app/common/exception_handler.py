# coding:utf-8
from copy import deepcopy
import traceback
from .logger import Logger
from .setting import DEBUG


def exceptionHandler(log: str, *default):
    """ decorator for exception handling

    Parameters
    ----------
    log: str
        log file name without `.log` suffix

    *default:
        the default value returned when an exception occurs
    """

    def outer(func):

        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseException as e:
                if DEBUG:
                    Logger(log).error(f"{e.__class__.__name__}: {traceback.format_exc()}")

                value = deepcopy(default)
                if len(value) == 0:
                    return None
                elif len(value) == 1:
                    return value[0]

                return value

        return inner

    return outer


def exceptionTracebackHandler(log: str, *default):
    """ decorator for exception handling

    Parameters
    ----------
    log: str
        log file name without `.log` suffix

    *default:
        the default value returned when an exception occurs
    """

    def outer(func):

        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseException as e:
                Logger(log).error(f"{e.__class__.__name__}: {traceback.format_exc()}")

                value = deepcopy(default)
                if len(value) == 0:
                    return None
                elif len(value) == 1:
                    return value[0]

                return value

        return inner

    return outer
