"""
Author: qianye
Date: 2025-06-23 08:19:26
LastEditTime: 2025-06-23 08:19:31
Description: 工具函数
"""
import logging
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import psutil
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

creationflags = 0
if sys.platform == "win32":
    creationflags = subprocess.CREATE_NO_WINDOW

def get_app_path():
    """
    使用 pathlib 获取程序根目录，兼容脚本和打包情况。
    在PyInstaller打包后，正确处理资源文件路径。
    """
    if getattr(sys, 'frozen', False):
        # 打包后的路径 - 使用sys._MEIPASS获取资源目录
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller打包后，资源文件在_MEIPASS目录下
            base_path = Path(sys._MEIPASS)
        else:
            # 其他打包工具的fallback
            base_path = Path(sys.executable).parent
    else:
        # 脚本运行的路径
        # .resolve() 可以获取绝对路径，避免相对路径问题
        base_path = Path(__file__).resolve().parent.parent.parent
    return base_path

def openLocalFile(file_path):
    if platform.system() == "Windows":
        # Windows 使用 Explorer 打开文件夹并选中文件
        subprocess.run(['explorer', '/select,', file_path])
    elif platform.system() == "Darwin":
        # macOS 使用 Finder 打开文件夹并选中文件
        subprocess.run(['open', '-R', file_path])

def getSystemProxy() -> Optional[str]:
    """
    获取系统代理设置。

    依次尝试以下方式：
    1. Windows: 从注册表读取代理设置。
    2. macOS: 使用 `scutil --proxy` 命令获取代理。
    3. 所有平台: 检查环境变量 `http_proxy` 和 `HTTP_PROXY`。

    :return: 代理 URL 字符串 (例如 "http://127.0.0.1:7890" 或 PAC 文件 URL)，
             如果未找到代理则返回 None。
    """
    proxy = None
    if sys.platform == "win32":
        proxy = _get_windows_proxy()
    elif sys.platform == "darwin":
        proxy = _get_macos_proxy()
    
    # 如果平台特定方法没有找到代理，则回退到检查环境变量
    # 环境变量是通用的，可以作为所有平台的最后手段
    if proxy:
        return proxy
        
    return os.environ.get('http_proxy') or os.environ.get('HTTP_PROXY')

def _get_windows_proxy() -> Optional[str]:
    """辅助函数：获取 Windows 系统的代理。"""
    try:
        # winreg 是 Windows 特有模块，在需要时才导入
        import winreg

        registry_path = r'Software\Microsoft\Windows\CurrentVersion\Internet Settings'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
            # 检查代理是否启用，ProxyEnable 的值为 1 (启用) 或 0 (禁用)
            proxy_enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
            if not proxy_enable:
                return None

            # 获取代理服务器地址，这个键可能不存在，所以单独处理
            try:
                proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')
                # 确保返回的 proxy_server 不为空
                if proxy_server:
                    # 代理字符串可能包含多个协议（如 "http=...;https=..."）
                    # 最简单的通用做法是直接返回，让使用者（如 requests）处理。
                    # 如果需要确保返回的是一个简单的 http 代理，可以做进一步处理。
                    # 这里我们假设它是一个简单的 "host:port" 格式，并添加协议头。
                    if not proxy_server.startswith(('http://', 'https://', 'socks://')):
                         return "http://" + proxy_server
                    return proxy_server
            except FileNotFoundError:
                # 代理启用但未设置服务器地址，这是一种正常情况
                logging.debug("Proxy is enabled but ProxyServer value is not set.")
                return None

    except (FileNotFoundError, ImportError) as e:
        # FileNotFoundError: 注册表项不存在
        # ImportError: 在非 Windows 系统上意外运行此代码
        logging.debug(f"Could not read Windows proxy settings: {e}")
    except Exception as e:
        # 捕获其他未知错误，并记录日志，而不是让程序崩溃
        logging.error(f"An unexpected error occurred while reading Windows proxy settings: {e}")
    
    return None

def _get_macos_proxy() -> Optional[str]:
    """辅助函数：获取 macOS 系统的代理。"""
    try:
        # 使用 subprocess 替代 os.popen，它更安全、更强大
        command = ['scutil', '--proxy']
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=5)
        
        # 使用正则表达式从输出中解析键值对
        proxy_settings = dict(re.findall(r'^\s+([A-Z][\w\d]+)\s+:\s+(.*)$', result.stdout, re.MULTILINE))

        # 检查 HTTP 代理
        if proxy_settings.get('HTTPEnable') == '1':
            host = proxy_settings.get('HTTPProxy')
            port = proxy_settings.get('HTTPPort')
            if host and port and port != '0':
                return f"http://{host}:{port}"

        # 检查自动代理配置 (PAC)
        if proxy_settings.get('ProxyAutoConfigEnable') == '1':
            pac_url = proxy_settings.get('ProxyAutoConfigURLString')
            if pac_url:
                return pac_url

    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        # CalledProcessError: scutil 命令执行失败
        # FileNotFoundError: scutil 命令不存在
        # TimeoutExpired: 命令执行超时
        logging.debug(f"Could not execute 'scutil --proxy': {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while reading macOS proxy settings: {e}")
        
    return None

def openConfigFile(file_path):
    if platform.system() == 'Darwin':
        #打开配置文件
        subprocess.run(['open',"-a", "TextEdit",file_path])
        
    else:
        subprocess.run(['start','notepad',file_path],creationflags=creationflags)

def openUrl(url: str):
    if not url.startswith("http"):
        if not Path(url).exists():
            return False
        QDesktopServices.openUrl(QUrl.fromLocalFile(url))
    else:
        QDesktopServices.openUrl(QUrl(url))

    return True

def checkAlistExist(directory):
    """检查目录下是否存在Alist主程序"""
    # 检查Windows系统
    if sys.platform == "win32":
        if (
            Path(directory, "openlist.exe").exists()
            or Path(directory, "alist.exe").exists()
        ):
            return True

    # 检查MacOS系统
    elif sys.platform == "darwin":
        if Path(directory, "openlist").exists() or Path(directory, "alist").exists():
            return True
        

    return False

def checkRcloneExist(directory):
    """检查目录下是否存在Rclone主程序"""
    # 检查Windows系统
    if sys.platform == "win32":
        # 判断是否存在rclone.exe文件，使用pathlib库
        if (
            Path(directory, "rclone.exe").exists()
        ):
            return True

    # 检查MacOS系统
    elif sys.platform == "darwin":
        if Path(directory, "rclone").exists():
            return True
        

    return False

# 获取alist主程序路径
def getAlistPath(directory):
    """获取Alist主程序路径"""
    if sys.platform == "win32":
        if Path(directory, "openlist.exe").exists():
            return Path(directory, "openlist.exe")
        elif Path(directory, "alist.exe").exists():
            return Path(directory, "alist.exe")
    elif sys.platform == "darwin":
        if Path(directory, "openlist").exists():
            return Path(directory, "openlist")
        elif Path(directory, "alist").exists():
            return Path(directory, "alist")

def getRclonePath(directory):
    """获取Rclone主程序路径"""
    if sys.platform == "win32":
        if Path(directory, "rclone.exe").exists():
            return Path(directory, "rclone.exe")
    elif sys.platform == "darwin":
        if Path(directory, "rclone").exists():
            return Path(directory, "rclone")
    return None

def isAlistRunning():
    """获取Alist主程序进程ID"""
    if sys.platform == "win32":
        for p in psutil.process_iter():
            if p.name() == "openlist.exe":
                return p.pid
            elif p.name() == "alist.exe":
                return p.pid
    elif sys.platform == "darwin":
        for p in psutil.process_iter():
            if p.name() == "openlist":
                return p.pid
            elif p.name() == "alist":
                return p.pid
    return None


def getAlistProcessName(directory):
    """获取Alist主程序进程名"""
    if sys.platform == "win32":
        if Path(directory, "openlist.exe").exists():
            return "openlist.exe"
        elif Path(directory, "alist.exe").exists():
            return "alist.exe"
    elif sys.platform == "darwin":
        if Path(directory, "openlist").exists():
            return "openlist"
        elif Path(directory, "alist").exists():
            return "alist"
    return None

def killProcess():
    killAlistProcess()
    killRcloneProcess()
def killAlistProcess():
    """
    杀掉Alist主程序进程
    同时清理alist和openlist进程
    使用subprocess.Popen执行系统命令：Windows使用taskkill，Mac/Linux使用killall
    Windows下禁用命令行窗口显示
    
    Returns:
        dict: 包含执行结果的字典，包括命令、返回码和消息
    """
    
    result = {
        'command': [],
        'success': False,
        'return_code': [],
        'message': '',
        'killed_processes': []
    }
    
    # 定义要清理的进程列表
    target_processes = ["alist", "openlist"]
    if sys.platform == "win32":
        target_processes = ["alist.exe", "openlist.exe"]
    
    success_count = 0
    # total_processes = len(target_processes)
    
    try:
        for target_process in target_processes:
            process_result = {
                'process': target_process,
                'success': False,
                'return_code': None,
                'message': ''
            }
            
            try:
                if sys.platform == "win32":
                    # Windows系统使用taskkill命令
                    cmd = ["taskkill", "/F", "/IM", target_process, "/T"]
                    
                    # 使用Popen执行命令
                    process = subprocess.run(
                        cmd,
                        creationflags=creationflags
                    )
                    
                else:
                    # Mac/Linux系统使用killall命令
                    base_process = target_process.replace(".exe", "")
                    cmd = ["killall", "-9", base_process]
                    
                    # 使用Popen执行命令
                    process = subprocess.run(cmd)
                
                result['command'].append(' '.join(cmd))
                
                # 等待进程完成，设置超时
                try:
                    return_code = process.wait(timeout=10)
                    process_result['return_code'] = return_code
                    result['return_code'].append(return_code)
                    
                    if return_code == 0:
                        process_result['success'] = True
                        process_result['message'] = f"成功终止{target_process}进程"
                        result['killed_processes'].append(target_process)
                        success_count += 1
                    else:
                        # 对于killall和taskkill，返回码非0通常表示进程不存在
                        process_result['success'] = True
                        process_result['message'] = f"未找到{target_process}进程（可能已经停止）"
                        success_count += 1
                                            
                except subprocess.TimeoutExpired:
                    # 超时处理
                    process.kill()
                    process.wait()  # 等待进程清理
                    
            except FileNotFoundError:
                pass
                
            except Exception:
                pass
        
        # # 设置整体结果
        # if success_count == total_processes:
        #     result['success'] = True
        #     result['message'] = f"成功处理所有进程，共清理了{len(result['killed_processes'])}个进程"
        # elif success_count > 0:
        #     result['success'] = True
        #     result['message'] = f"部分成功，共处理{success_count}/{total_processes}个进程，清理了{len(result['killed_processes'])}个进程"
        # else:
        #     result['message'] = "未能成功处理任何进程"
            
    except Exception:
        pass
        # result['message'] = f"执行进程清理时发生错误: {e}"
        # print(result['message'])
    
    return result


def killRcloneProcess():
    """
    杀掉Rclone主程序进程
    使用subprocess.Popen执行系统命令：Windows使用taskkill，Mac/Linux使用killall
    Windows下禁用命令行窗口显示
    
    Returns:
        dict: 包含执行结果的字典，包括命令、返回码和消息
    """
    
    result = {
        'command': '',
        'success': False,
        'return_code': None,
        'message': ''
    }
    
    try:
        if sys.platform == "win32":
            # Windows系统使用taskkill命令
            cmd = ["taskkill", "/F", "/IM", "rclone.exe", "/T"]

            # 使用Popen执行命令
            process = subprocess.run(
                cmd,
                creationflags=creationflags
            )
            
        else:
            # Mac/Linux系统使用killall命令
            cmd = ["killall", "-9", "rclone"]
            
            # 使用Popen执行命令
            process = subprocess.run(cmd)
        
        result['command'] = ' '.join(cmd)
        
        # 等待进程完成，设置超时
        try:
            return_code = process.wait(timeout=10)  # noqa: F841
            # result['return_code'] = return_code
            
            # if return_code == 0:
            #     result['success'] = True
            #     result['message'] = "成功终止rclone进程"
            # else:
            #     # 对于killall和taskkill，返回码非0通常表示进程不存在
            #     result['success'] = True
            #     result['message'] = "未找到rclone进程（可能已经停止）"
            
            # print(result['message'])
                
        except subprocess.TimeoutExpired:
            # 超时处理
            process.kill()
            process.wait()  # 等待进程清理
            # result['message'] = "终止进程命令执行超时"
            # print(result['message'])
            
    except FileNotFoundError:
        pass
        # if sys.platform == "win32":
        #     result['message'] = "未找到taskkill命令"
        # else:
        #     result['message'] = "未找到killall命令"
        # print(result['message'])
        
    except Exception:
        pass
        # result['message'] = f"终止Rclone进程时发生错误: {e}"
        # print(result['message'])
    
    return result
