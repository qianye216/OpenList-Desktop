'''
Author: qianye
Date: 2024-12-14 09:41:27
LastEditTime: 2025-06-23 18:03:39
Description: 添加开机启动
'''
import sys
import os

if sys.platform == "win32":
    import winreg
elif sys.platform == "darwin":
    import plistlib
else:
    raise ImportError


REGISTRY_NAME = "OpenList_Desktop_By_Shimily"
MAC_APP_LABEL = "com.shimily.openlist_desktop"
MAC_PLIST_LOCATION = os.path.expanduser(f"~/Library/LaunchAgents/{MAC_APP_LABEL}.plist")


def add_to_startup(filename=f"{os.path.abspath(sys.argv[0])}"):
    if sys.platform == "win32":
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, REGISTRY_NAME, 0, winreg.REG_SZ, filename)
        key.Close()
    elif sys.platform == "darwin":
        create_plist_mac(filename, True)


def create_plist_mac(filename, state):
    plist_filename = [filename]
    plist_info = {
        "ProgramArguments": plist_filename,
        "ProcessType": "Interactive",
        "Label": MAC_APP_LABEL,
        "KeepAlive": False,
        "RunAtLoad": state,
    }
    os.makedirs(os.path.split(MAC_PLIST_LOCATION)[0], exist_ok=True)
    with open(MAC_PLIST_LOCATION, "wb") as f:
        plistlib.dump(plist_info, f)


def update_plist_mac(state):
    if check_startup() != state:
        try:
            with open(MAC_PLIST_LOCATION, "rb") as f:
                plist_info = plistlib.load(f)
            plist_info["RunAtLoad"] = state
            with open(MAC_PLIST_LOCATION, "wb") as f:
                plistlib.dump(plist_info, f)
        except FileNotFoundError:
            create_plist_mac(state)


def remove_from_startup():
    if sys.platform == "win32":
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.DeleteValue(key, REGISTRY_NAME)
            key.Close()
        except Exception:
            pass
    elif sys.platform == "darwin":
        update_plist_mac(False)


def check_startup():
    if sys.platform == "win32":
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        i = 0
        while True:
            try:
                a = winreg.EnumValue(key, i)
                i += 1
                if a[0] == REGISTRY_NAME:
                    return True
            except OSError:
                break
        key.Close()
        return False
    elif sys.platform == "darwin":
        try:
            with open(MAC_PLIST_LOCATION, "rb") as f:
                a = plistlib.load(f)
            return a["RunAtLoad"]
        except FileNotFoundError:
            return False
