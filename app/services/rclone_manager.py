# file: services/rclone_manager.py
import os
import platform
import re
import subprocess
import sys
from typing import Optional

import httpx
from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from ..common.concurrent import TaskExecutor
from ..common.config import cfg
from ..common.utils import checkRcloneExist, getRclonePath, getSystemProxy

creationflags = 0
if sys.platform == "win32":
    creationflags = subprocess.CREATE_NO_WINDOW

class RcloneManager(QObject):
    """
    Rclone 服务管理器 (HTTP API 版本)
    - 使用一个核心 rclone rcd 进程处理所有操作，包括配置和挂载。
    - 所有挂载/卸载操作均通过发送 HTTP 请求到 rcd 服务的 API 端点完成。
    """

    # --- 核心服务信号 ---
    coreServiceStateChanged = Signal(bool, str)  # is_running, rc_url
    logMessageReady = Signal(str)
    errorOccurred = Signal(str)
    configurationRequired = Signal()  # 新增：配置需求信号

    # --- 状态更新信号 ---
    mountsInfoUpdated = Signal(list)  # list[dict] of detailed mount infos
    remotesUpdated = Signal(list)  # list[str] of remote names

    # 添加新的信号
    versionInfoReady = Signal(str)  # 版本信息准备就

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._core_process: Optional[QProcess] = None
        self.is_core_running = False
        self.rc_url: Optional[str] = None
        self.rc_user: Optional[str] = None
        self.rc_pass: Optional[str] = None
        self._is_stopping = False  # Flag to prevent multiple stop calls
        
        # 添加日志存储
        self._log_messages = []  # 存储日志消息
        self._max_log_lines = 1000  # 最大日志行数

        # HTTP 客户端，可重用
        self._http_client = httpx.Client(
            proxy=getSystemProxy(), timeout=10, follow_redirects=True
        )

        # 定时器，用于定期刷新挂载状态
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(5000)  # 每5秒检查一次
        self._status_timer.timeout.connect(self.refresh_mounts_info)
    
    def _add_log_message(self, message: str):
        """
        添加日志消息到内存存储
        
        :param message: str, 日志消息
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self._log_messages.append(formatted_message)
        
        # 限制日志行数，避免内存占用过多
        if len(self._log_messages) > self._max_log_lines:
            self._log_messages = self._log_messages[-self._max_log_lines:]
    
    def get_log_messages(self) -> list:
        """
        获取所有日志消息
        
        :return: list, 日志消息列表
        """
        return self._log_messages.copy()
    
    def clear_log_messages(self):
        """
        清空日志消息
        """
        self._log_messages.clear()
        self.logMessageReady.emit("日志已清空")

    def get_rclone_version_info(self) -> str:
        """
        获取 Rclone 版本信息

        :return: str, 版本信息字符串
        """
        rclone_path = self._get_rclone_path()
        if not rclone_path:
            return None

        try:
            result = subprocess.run(
                [rclone_path, "version"], capture_output=True, text=True, timeout=5,creationflags=creationflags
            )
            version_info = result.stdout if result.returncode == 0 else result.stderr
            self.logMessageReady.emit(
                f"获取Rclone版本信息: {version_info.split()[0] if version_info else '未知'}"
            )
            return version_info
        except Exception:
            return None
        
    def get_rclone_version_number(self) -> str:
        """
        获取 Rclone 具体版本号
        
        从完整的版本信息中提取版本号，例如从 "rclone v1.64.2" 中提取 "1.64.2"
        
        :return: str, 版本号字符串，如果获取失败则返回错误信息
        """
        rclone_path = self._check_rclone_work_directory()
        if not rclone_path:
            return "Rclone路径未配置"

        try:
            result = subprocess.run(
                [rclone_path, "version"], capture_output=True, text=True, timeout=5,creationflags=creationflags
            )
            
            if result.returncode != 0:
                error_msg = f"获取版本号失败: {result.stderr}"
                self.errorOccurred.emit(error_msg)
                return error_msg
                
            version_output = result.stdout.strip()
            if not version_output:
                error_msg = "版本信息为空"
                self.errorOccurred.emit(error_msg)
                return error_msg
                
            # 从输出中提取版本号
            # 通常格式为: "rclone v1.64.2" 或类似格式
            lines = version_output.split('\n')
            first_line = lines[0].strip()
            
            # 查找版本号模式
            version_pattern = r"v(\d+\.\d+\.\d+)"
            match = re.search(version_pattern, first_line)
            
            if match:
                version_number = match.group(1)
                self.logMessageReady.emit(f"获取Rclone版本号: {version_number}")
                return version_number
            else:
                # 如果无法匹配标准版本格式，返回第一行作为版本信息
                self.logMessageReady.emit(f"获取Rclone版本信息: {first_line}")
                return first_line
                
        except Exception as e:
            error_msg = f"获取版本号失败: {e}"
            self.errorOccurred.emit(error_msg)
            return error_msg

    def get_rclone_version_async(self):
        """
        异步获取 Rclone 版本信息并通过信号发送
        """
        version_info = self.get_rclone_version()
        self.versionInfoReady.emit(version_info)

    def _get_rc_auth_from_config(self):
        """从配置中解析RC认证信息"""
        args = cfg.get(cfg.rcloneStartupParams) or []
        if isinstance(args, str):
            args = args.split()

        try:
            user_index = args.index("--rc-user")
            self.rc_user = args[user_index + 1]
            pass_index = args.index("--rc-pass")
            self.rc_pass = args[pass_index + 1]
            self._http_client.auth = (self.rc_user, self.rc_pass)
        except (ValueError, IndexError):
            self.rc_user, self.rc_pass, self._http_client.auth = None, None, None
            self.logMessageReady.emit(
                "警告: Rclone 启动参数中未找到 --rc-user 或 --rc-pass，API请求可能失败。"
            )

    def _check_rclone_work_directory(self) -> Optional[str]:
        rclone_dir = cfg.rcloneWorkDirectory.value
        if not checkRcloneExist(rclone_dir):
            return None
        return str(getRclonePath(rclone_dir))

    def _get_rclone_path(self) -> Optional[str]:
        """检查并返回rclone可执行文件路径"""
        rclone_dir = cfg.rcloneWorkDirectory.value
        if not checkRcloneExist(rclone_dir):
            # 触发配置需求信号而不是直接发送错误
            self.configurationRequired.emit()
            return None
        return str(getRclonePath(rclone_dir))

    # --- 核心 RCD 服务管理 ---

    def start_core_service(self):
        """启动核心的 Rclone RC (rcd) 服务"""
        if (
            self.is_core_running
            and self._core_process
            and self._core_process.state() != QProcess.ProcessState.NotRunning
        ):
            self.logMessageReady.emit("Rclone 核心服务已在运行。")
            return

        rclone_path = self._get_rclone_path()
        if not rclone_path:
            return

        args = cfg.get(cfg.rcloneStartupParams) or []
        if isinstance(args, str):
            args = args.split()

        if "rcd" not in args:
            self.errorOccurred.emit(
                "启动失败: Rclone 启动参数必须包含 'rcd' 以启用API服务。"
            )
            return

        self._get_rc_auth_from_config()

        args = [arg for arg in args if arg.strip()]
        self._core_process = QProcess()
        self._core_process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )
        self._core_process.readyRead.connect(self._handle_core_output)
        self._core_process.finished.connect(self._on_core_process_finished)

        self.logMessageReady.emit(f"启动 Rclone 核心服务: rclone {' '.join(args)}")
        self._core_process.start(rclone_path, args)

    def stop_core_service(self):
        """停止核心服务 (异步)"""
        if not self.is_core_running or self._is_stopping:
            return

        rclone_path = self._get_rclone_path()
        if not rclone_path:
            return

        if (
            self._core_process
            and self._core_process.state() != QProcess.ProcessState.NotRunning
        ):
            self._is_stopping = True
            self.logMessageReady.emit("正在停止 Rclone 核心服务...")

            def unmount_task():
                # This is a blocking call, so it's run in a thread
                return self._send_rc_command("/mount/unmountall")

            def on_unmount_finished(response):
                if "error" not in response:
                    self.logMessageReady.emit("所有挂载点卸载请求已发送。")
                else:
                    error_msg = (
                        response.get("error", "未知API错误") if response else "请求失败"
                    )
                    self.errorOccurred.emit(f"卸载所有挂载点失败: {error_msg}")

                # Now that unmounting is done (or failed), terminate the process
                self._terminate_core_process()

            TaskExecutor.runTask(unmount_task).then(on_unmount_finished)

    def restart_core_service(self):
        """重启核心服务"""
        if not self.is_core_running:
            self.start_core_service()
            return

        if self._core_process:
            self._core_process.setProperty("restarting", True)
            self.stop_core_service()

    def _terminate_core_process(self):
        """终止核心进程 (非阻塞)"""
        if (
            self._core_process
            and self._core_process.state() != QProcess.ProcessState.NotRunning
        ):
            self._core_process.terminate()

            # Use a timer to forcefully kill if it doesn't terminate gracefully.
            def check_termination():
                if (
                    self._core_process
                    and self._core_process.state() != QProcess.ProcessState.NotRunning
                ):
                    self.logMessageReady.emit("核心服务未在3秒内响应，强制终止...")
                    self._core_process.kill()

            QTimer.singleShot(3000, check_termination)

    def _handle_core_output(self):
        output = self._read_process_output(self._core_process)
        for line in output.splitlines():
            if not line.strip():
                continue
            log_message = f"[Core] {line}"
            self._add_log_message(log_message)  # 添加到日志存储
            self.logMessageReady.emit(log_message)
            if "Serving remote control on" in line and not self.is_core_running:
                self.is_core_running = True
                self.rc_url = line.split("on ")[-1].strip()
                self.coreServiceStateChanged.emit(True, self.rc_url)
                startup_message = f"Rclone 核心服务已在 {self.rc_url} 上线。"
                self._add_log_message(startup_message)
                self.logMessageReady.emit(startup_message)
                self._status_timer.start()
                QTimer.singleShot(500, self._initial_sync)

    def _initial_sync(self):
        """核心服务启动后的初始同步任务"""
        self.logMessageReady.emit("正在同步远程列表和 WebDAV 配置...")
        self.list_remotes()
        self._ensure_webdav_remote()
        self.refresh_mounts_info()  # 检查已有挂载
        self._auto_mount_on_startup()

    def _on_core_process_finished(self):
        restarting = False
        if self._core_process:
            try:
                # During shutdown, the QProcess C++ object might be deleted before this slot runs.
                restarting = self._core_process.property("restarting")
                self._core_process.setProperty("restarting", False)
            except RuntimeError:
                restarting = False  # Object is deleted, so it can't be restarting.

        self.is_core_running = False
        self.rc_url = None
        self._is_stopping = False  # Reset the flag
        self.coreServiceStateChanged.emit(False, "")
        self._status_timer.stop()
        self.mountsInfoUpdated.emit([])
        self.logMessageReady.emit("Rclone 核心服务已停止。")

        if restarting:
            self.logMessageReady.emit("正在重启 Rclone 核心服务...")
            QTimer.singleShot(1000, self.start_core_service)

    # --- API 通用交互 ---

    def _send_rc_command(
        self, endpoint: str, params: Optional[dict] = None
    ) -> Optional[dict]:
        """向 Rclone RC API 发送命令 (核心方法)"""
        if not self.is_core_running or not self.rc_url:
            self.errorOccurred.emit("Rclone 核心服务未运行，API命令无法发送。")
            return None
        try:
            full_url = f"{self.rc_url.rstrip('/')}{endpoint}"
            response = self._http_client.post(full_url, json=params or {})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_details = e.response.text
            self.errorOccurred.emit(
                f"Rclone API 错误 ({e.response.status_code}) on {endpoint}: {error_details}"
            )
            return {"error": error_details, "status_code": e.response.status_code}
        except httpx.RequestError as e:
            self.errorOccurred.emit(f"Rclone API 请求失败: {e}")
            return {"error": str(e), "status_code": -1}
        return None

    # --- 远程配置管理 ---

    def create_webdav_remote(self, name: str = "webdav"):
        """
        创建WebDAV远程配置

        :param name: str, 远程配置名称
        """
        rclone_path = self._get_rclone_path()
        if not rclone_path:
            return
        webdav_config = cfg.get(cfg.rcloneWebDavAccount) or {}

        # 检查必要的配置是否存在
        if not webdav_config.get("url") or not webdav_config.get("user"):
            self.errorOccurred.emit("WebDAV配置不完整，请先在设置中配置WebDAV账户")
            return

        # 使用配置中的值，只为vendor提供默认值
        parameters = {
            "url": webdav_config["url"],
            "user": webdav_config["user"],
            "pass": webdav_config.get("pass", ""),
            "vendor": webdav_config.get("vendor", "other"),
        }

        if "pass" in parameters and parameters["pass"]:
            obscured_pass = self._obscure_password(parameters["pass"])
            parameters["pass"] = obscured_pass if obscured_pass else parameters["pass"]

        self.create_remote(name, "webdav", parameters)

    def create_remote(self, name: str, remote_type: str, parameters: dict):
        params = {"name": name, "type": remote_type, "parameters": parameters}
        if self._send_rc_command("/config/create", params) is not None:
            self.logMessageReady.emit(f"成功创建/更新远程配置: {name}")
            self.list_remotes()

    def list_remotes(self):
        response = self._send_rc_command("/config/listremotes")
        if response and "remotes" in response:
            self.remotesUpdated.emit(response["remotes"])

    def update_remote(self, name: str, remote_type: str, parameters: dict) -> dict:
        """
        更新远程配置

        :param name: str, 远程配置名称
        :param remote_type: str, 远程类型（如 'webdav'）
        :param parameters: dict, 远程配置参数
        :return: dict, 包含操作结果的字典
        """
        if not self.is_core_running or not self.rc_url:
            error_msg = "Rclone 核心服务未运行，无法更新远程配置"
            self.errorOccurred.emit(error_msg)
            return {"success": False, "message": error_msg}

        # 处理密码加密
        if "pass" in parameters and parameters["pass"]:
            self.logMessageReady.emit("WebDAV密码已加密处理")
            obscured_pass = self._obscure_password(parameters["pass"])
            if obscured_pass:
                parameters["pass"] = obscured_pass

        params = {"name": name, "type": remote_type, "parameters": parameters}

        # 创建安全的日志记录参数（隐藏密码）
        safe_params = params.copy()
        if "parameters" in safe_params and "pass" in safe_params["parameters"]:
            safe_params["parameters"] = safe_params["parameters"].copy()
            safe_params["parameters"]["pass"] = "***隐藏***"

        self.logMessageReady.emit(f"更新远程配置: {safe_params}")
        response = self._send_rc_command("/config/update", params)

        if "error" not in response:
            self.logMessageReady.emit(f"成功更新远程配置: {name}")
            # 刷新远程列表
            self.list_remotes()
            return {"success": True, "message": f"远程配置 '{name}' 已更新"}
        else:
            error_msg = response.get("error", "未知API错误") if response else "请求失败"
            self.errorOccurred.emit(f"更新远程配置失败: {error_msg}")
            return {"success": False, "message": f"更新远程配置失败: {error_msg}"}

    def delete_remote(self, name: str) -> dict:
        """
        删除远程配置

        :param name: str, 要删除的远程配置名称
        :return: dict, 包含操作结果的字典
        """
        if not self.is_core_running or not self.rc_url:
            error_msg = "Rclone 核心服务未运行，无法删除远程配置"
            self.errorOccurred.emit(error_msg)
            return {"success": False, "message": error_msg}

        params = {"name": name}
        response = self._send_rc_command("/config/delete", params)
        if "error" not in response:
            self.logMessageReady.emit(f"成功删除远程配置: {name}")
            # 刷新远程列表
            self.list_remotes()
            return {"success": True, "message": f"远程配置 '{name}' 已删除"}
        else:
            error_msg = response.get("error", "未知API错误") if response else "请求失败"
            self.errorOccurred.emit(f"删除远程配置失败: {error_msg}")
            return {"success": False, "message": f"删除远程配置失败: {error_msg}"}

    # --- 挂载管理 (HTTP API 版本) ---

    def refresh_mounts_info(self):
        """通过API获取当前所有挂载点信息，并触发更新"""
        response = self._send_rc_command("/mount/listmounts")
        if response and "mountPoints" in response:
            self.mountsInfoUpdated.emit(response["mountPoints"])
        else:
            # 服务可能刚启动，还没准备好，或者没有挂载
            self.mountsInfoUpdated.emit([])

    def mount(self, mount_config: dict) -> dict:
        """通过API将远程挂载到本地"""
        mount_point = mount_config.get("mount_point")
        if not mount_point:
            return {"success": False, "message": "挂载失败: 未提供 'mount_point'。"}
        
        # 在挂载前确保 WebDAV 配置存在
        self._ensure_webdav_remote()
        
        # 平台兼容性处理：Windows盘符需要加冒号
        if (
            platform.system() == "Windows"
            and len(mount_point) == 1
            and mount_point.isalpha()
        ):
            mount_point_os = f"{mount_point}:"
        else:
            mount_point_os = mount_point
    
        # 构建API请求的 payload
        fs_value = mount_config["fs"]
        payload = {
            "fs": fs_value,
            "mountPoint": mount_point_os,
            "mountOpt": {
                "AllowOther": mount_config.get("network_mode", True),
                "AllowNonEmpty": True,
                "VolumeName": mount_config.get("name", "Rclone Mount").upper(),
                "ExtraFlags": (mount_config.get("extra_args", "")).split(),
            },
            "vfsOpt": {
                "CacheMode": {"off": 0, "minimal": 1, "writes": 2, "full": 3}.get(
                    mount_config.get("vfs_cache_mode", "off")
                ),
            },
        }
    
        self.logMessageReady.emit(f"发送挂载请求到API: {payload}")
        response = self._send_rc_command("/mount/mount", payload)
    
        if "error" not in response:
            self.logMessageReady.emit(f"挂载请求已成功发送: {mount_point}")
            QTimer.singleShot(1000, self.refresh_mounts_info)  # 延迟刷新状态
            return {"success": True, "message": f"挂载请求已发送: {mount_point}"}
        else:
            error_msg = response.get("error", "未知API错误") if response else "请求失败"
            return {"success": False, "message": f"挂载失败: {error_msg}"}

    def unmount(self, mount_point: str) -> dict:
        """通过API卸载一个挂载点"""
        # 平台兼容性处理
        if (
            platform.system() == "Windows"
            and len(mount_point) == 1
            and mount_point.isalpha()
        ):
            mount_point_os = f"{mount_point}:"
        else:
            mount_point_os = mount_point

        payload = {"mountPoint": mount_point_os}

        self.logMessageReady.emit(f"发送卸载请求到API: {payload}")
        response = self._send_rc_command("/mount/unmount", payload)

        if "error" not in response:
            self.logMessageReady.emit(f"卸载请求已成功发送: {mount_point}")
            QTimer.singleShot(1000, self.refresh_mounts_info)  # 延迟刷新状态
            return {"success": True, "message": f"卸载请求已发送: {mount_point}"}
        else:
            error_msg = response.get("error", "未知API错误") if response else "请求失败"
            return {"success": False, "message": f"卸载失败: {error_msg}"}

    def unmount_all(self):
        """通过API卸载所有挂载点"""
        self.logMessageReady.emit("正在通过API卸载所有挂载点...")
        response = self._send_rc_command("/mount/unmountall")

        if "error" not in response:
            self.logMessageReady.emit("卸载所有挂载点的请求已成功发送。")
            QTimer.singleShot(1000, self.refresh_mounts_info)
        else:
            error_msg = response.get("error", "未知API错误") if response else "请求失败"
            self.errorOccurred.emit(f"卸载所有挂载点失败: {error_msg}")

    # --- 工具方法 ---
    def _read_process_output(self, process: QProcess) -> str:
        try:
            return process.readAll().data().decode(errors="ignore")
        except Exception:
            return ""

    def _ensure_webdav_remote(self):
        """确保 WebDAV 远程配置存在"""
        response = self._send_rc_command("/config/listremotes")
        
        # [修复] 检查 response 是否有效，以及 "remotes" 键的值是否为列表。
        # 这可以防止因 API 返回 {"remotes": null} 或其他意外格式而导致的 TypeError。
        if response and isinstance(response.get("remotes"), list):
            remotes_list = response["remotes"]
            if "webdav" not in remotes_list:
                self.logMessageReady.emit("未找到 'webdav' 远程配置，正在自动创建...")
                self.create_webdav_remote("webdav")
            else:
                self.logMessageReady.emit("WebDAV 远程配置已存在。")
        else:
            # 如果 response 不为 None 但格式不正确，则记录日志。
            # 如果 response 本身是 None，则 _send_rc_command 内部已经发出了错误信号。
            if response:
                error_info = response.get("error", f"API响应格式不正确: {response}")
                self.logMessageReady.emit(f"检查 WebDAV 配置失败：{error_info}")
            # 在无法确认远程列表的情况下，不执行任何操作，避免引入更多问题。

    def _obscure_password(self, password: str) -> str:
        """使用rclone obscure命令加密密码"""
        rclone_path = self._get_rclone_path()
        if not rclone_path:
            return password  # 如果路径未配置，返回原密码
        try:
            result = subprocess.run(
                [rclone_path, "obscure", password],
                capture_output=True,
                creationflags=creationflags,
                text=True,
                timeout=5,
                check=True,
            )
            return result.stdout.strip()
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ) as e:
            self.logMessageReady.emit(f"密码加密失败: {e}")
            return None

    def _auto_mount_on_startup(self):
        """在核心服务启动后，自动挂载标记为自动启动的配置"""
        mount_configs = cfg.get(cfg.mountConfigs) or []
        auto_mount_configs = [c for c in mount_configs if c.get("auto_mount", False)]

        if not auto_mount_configs:
            return

        self.logMessageReady.emit(
            f"发现 {len(auto_mount_configs)} 个自动挂载项，准备挂载..."
        )

        def start_auto_mounts():
            for config in auto_mount_configs:
                mount_point = config.get("mount_point")
                if not mount_point:
                    continue
                # 检查挂载点目录是否存在，不存在则创建
                if not os.path.exists(mount_point):
                    os.makedirs(mount_point, exist_ok=True)
                self.logMessageReady.emit(
                    f"自动挂载: {config.get('name')} -> {mount_point}"
                )
                self.mount(config)

        QTimer.singleShot(2000, start_auto_mounts)
        
    def unmount_all_fallback(self):
        """
        后备卸载方法，用于在API卸载失败或进程无法正常终止时，强制清理挂载点。
        """
        mount_configs = cfg.get(cfg.mountConfigs) or []
        if not mount_configs:
            return

        self.logMessageReady.emit("执行后备卸载流程...")
        for config in mount_configs:
            mount_point = config.get("mount_point")
            if not mount_point:
                continue

            try:
                # 检查挂载点是否真的还被挂载
                if platform.system() == "Windows":
                    # 在Windows上，可以用`net use`或检查目录是否为挂载点
                    # 这里用一个简单的方法：如果目录存在但为空，可能就是个残留的挂载点
                    if os.path.exists(mount_point) and not os.listdir(mount_point):
                         self.logMessageReady.emit(f"发现残留的Windows挂载点: {mount_point}")
                         # pass # 暂不处理，因为fsutil需要管理员权限

                elif platform.system() == "Darwin":
                    # 在macOS上，使用 `mount` 命令检查
                    result = subprocess.run(["mount"], capture_output=True, text=True)
                    if mount_point in result.stdout:
                        self.logMessageReady.emit(f"发现残留的macOS挂载点: {mount_point}, 尝试强制卸载...")
                        # 使用diskutil或umount强制卸载
                        subprocess.run(["diskutil", "unmount", "force", mount_point], check=True)

            except Exception as e:
                self.errorOccurred.emit(f"后备卸载 {mount_point} 失败: {e}")

    def cleanup(self):
        """
        在应用退出时清理所有进程和挂载点。
        """
        self.logMessageReady.emit("开始执行清理流程...")
        
        # 1. 优雅地停止核心服务（会尝试API卸载）
        self.stop_core_service()

        # 2. 执行后备强制卸载
        self.unmount_all_fallback()

        self.logMessageReady.emit("清理流程完成。")


# 创建服务的单例实例
rcloneManager = RcloneManager()



