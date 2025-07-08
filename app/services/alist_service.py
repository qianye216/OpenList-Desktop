# file: services/alist_service.py

import re
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QProcess, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from ..common.config import cfg
from ..common.signal_bus import signalBus
from ..common.utils import checkAlistExist, getAlistPath, openConfigFile

creationflags = 0
if sys.platform == "win32":
    creationflags = subprocess.CREATE_NO_WINDOW

class AlistService(QObject):
    """
    Alist 服务管理类 (单例)
    封装所有与 Alist 命令行工具的交互。
    """

    # --- 信号定义 ---
    stateChanged = Signal(bool, str, int)
    logMessageReady = Signal(str)
    passwordReady = Signal(str, str)
    versionReady = Signal(str)
    twoFactorAuthDisabled = Signal()
    errorOccurred = Signal(str)
    configurationRequired = Signal()
    operationFailed = Signal(str)  # 新增信号，用于操作失败（如文件未找到）

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._main_process: Optional[QProcess] = None
        self.is_running = False
        self.port: Optional[int] = None
        self.url: Optional[str] = None
        self.pid: Optional[int] = None

    def _run_command(
        self, args: list, on_ready_read: callable, on_finished: callable = None
    ):
        """执行alist命令的通用方法"""
        alist_path = self._check_alist_work_directory()
        if not alist_path:
            self.configurationRequired.emit()
            return None

        process = QProcess()
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyRead.connect(lambda: on_ready_read(process))
        if on_finished:
            process.finished.connect(lambda: on_finished(process))

        # 动态获取可执行文件名称用于日志显示
        executable_name = Path(alist_path).stem  # 获取不带扩展名的文件名
        self.logMessageReady.emit(
            self._format_log_line(f"执行命令: {executable_name} {' '.join(args)}", "INFO")
        )
        process.start(alist_path, args)
        return process

    def start(self):
        """启动 Alist 服务 (已优化)"""
        if self.is_running and self._main_process:
            self.logMessageReady.emit(self._format_log_line("服务已在运行中。", "WARN"))
            return

        args = ["server"]
        args.extend(self._get_common_startup_args())  # 添加通用启动参数

        self._main_process = self._run_command(
            args=args,
            on_ready_read=self._handle_main_output,
            on_finished=self._on_main_process_finished,
        )

    def stop(self):
        """停止 Alist 服务"""
        if not self.is_running or not self._main_process:
            self.logMessageReady.emit(self._format_log_line("服务未运行。", "WARN"))
            return
        self._main_process.terminate()
        if not self._main_process.waitForFinished(3000):
            self._main_process.kill()

    def restart(self):
        """重启 Alist 服务"""
        if self.is_running and self._main_process:
            self._main_process.setProperty("restarting", True)
            self.stop()
        else:
            self.start()

    def getRandomPassword(self):
        """获取随机管理员密码 (已优化)"""
        args = ["admin", "random"]
        args.extend(self._get_common_startup_args())  # 添加通用启动参数
        self._run_command(
            args=args,
            on_ready_read=self._handle_password_output,
        )

    def setPassword(self, password: str):
        """设置新的管理员密码 (已优化)"""
        args = ["admin", "set", password]
        args.extend(self._get_common_startup_args())  # 添加通用启动参数
        self._run_command(
            args=args,
            on_ready_read=self._handle_password_output,
        )

    def getVersion(self):
        """获取 Alist 版本信息 (此命令不依赖数据目录，无需额外参数)"""
        self._run_command(args=["version"], on_ready_read=self._handle_version_output)
        
    def getVersionNumber(self) -> str:
        """
        获取 Alist 具体版本号（同步方法）
        
        直接返回版本号字符串，不通过信号传递
        
        Returns
        -------
        str
            版本号字符串，如果获取失败则返回错误信息
        """
       
        
        alist_path = self._check_alist_work_directory()
        if not alist_path:
            return "Alist路径未配置"
        
        try:
            # 直接执行版本命令
            result = subprocess.run(
                [alist_path, "version"], 
                capture_output=True, 
                creationflags=creationflags,
                text=True, 
                timeout=5
            )
            
            if result.returncode != 0:
                error_msg = f"获取版本号失败: {result.stderr}"
                self.logMessageReady.emit(self._format_log_line(error_msg, "ERROR"))
                return error_msg
                
            version_output = result.stdout.strip()
            if not version_output:
                error_msg = "版本信息为空"
                self.logMessageReady.emit(self._format_log_line(error_msg, "ERROR"))
                return error_msg
                
            # 从输出中提取版本号
            # 新格式示例:
            # Built At: 2025-06-22 07:33:33 +0000
            # Go Version: go1.24.1 darwin/arm64
            # Author: The OpenList Projects Contributors
            # Commit ID: 639b5cf7
            # Version: v4.0.1
            # WebVersion: v4.0.1
            
            lines = version_output.split('\n')
            
            # 查找 "Version:" 行
            for line in lines:
                line = line.strip()
                if line.startswith("Version:"):
                    # 提取版本号，格式为 "Version: v4.0.1"
                    version_part = line.split(":", 1)[1].strip()
                    # 移除可能的 'v' 前缀
                    version_number = version_part.lstrip('v')
                    return version_number
            
            # 如果没有找到 "Version:" 行，尝试旧的解析方式作为备用
            first_line = lines[0].strip()
            version_pattern = r"v?(\d+\.\d+\.\d+(?:-[\w\.-]+)?)"
            match = re.search(version_pattern, first_line)
            
            if match:
                version_number = match.group(1)
                return version_number
            else:
                return version_output
                
        except subprocess.TimeoutExpired:
            return error_msg
        except Exception as e:
            error_msg = f"获取版本号失败: {e}"
            return error_msg

    def disable2FA(self):
        """禁用双重验证 (已优化)"""
        args = ["cancel2fa"]
        args.extend(self._get_common_startup_args())  # 添加通用启动参数
        self._run_command(args=args, on_ready_read=self._handle_2fa_output)

    def open_config_file(self):
        """打开 Alist 的配置文件，会根据启动参数智能判断路径"""
        data_path = self._get_data_directory_path()
        if not data_path:
            # configurationRequired 或 operationFailed 信号已被发出
            return

        config_file = data_path / "config.json"
        signalBus.warning_Signal.emit("配置文件路径："+str(config_file))
        if config_file.exists() and config_file.is_file():
            openConfigFile(config_file)
        else:
            self.operationFailed.emit("未找到配置文件！")

    def open_log_dir(self):
        """打开 Alist 的日志目录，会根据启动参数智能判断路径"""
        data_path = self._get_data_directory_path()
        if not data_path:
            # configurationRequired 或 operationFailed 信号已被发出
            return

        log_dir = data_path / "log"
        if log_dir.exists() and log_dir.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir)))
        else:
            self.operationFailed.emit("未找到日志目录！")

    def cleanup(self):
        """在应用退出时清理进程"""
        if (
            self._main_process
            and self._main_process.state() != QProcess.ProcessState.NotRunning
        ):
            self._main_process.setProperty("restarting", False)
            self.stop()

    # --- 私有槽函数和处理器 (保持不变) ---
    def _handle_main_output(self, process: QProcess):
        output = self._read_process_output(process)
        for line in output.splitlines():
            if not line.strip():
                continue
            self.logMessageReady.emit(self._format_log_line(line))
            if "start HTTP server @" in line:
                self.is_running = True
                self.port = int(line.split("@")[1].split(":")[1])
                self.url = f"http://localhost:{self.port}"
                self.pid = process.processId()
                self.stateChanged.emit(True, self.url, self.pid)

    def _on_main_process_finished(self, process: QProcess):
        self.is_running = False
        self.port = None
        self.url = None
        self.pid = None
        self.stateChanged.emit(False, "", -1)
        self.logMessageReady.emit(self._format_log_line("服务已停止。", "INFO"))
        if process.property("restarting"):
            self.start()

    def _handle_password_output(self, process: QProcess):
        output = self._read_process_output(process)
        for line in output.splitlines():
            if not line.strip():
                continue
            self.logMessageReady.emit(self._format_log_line(line))
        username, password = None, None
        for line in output.split("\n"):
            if "username:" in line:
                username = line.split("username:")[1].strip()
            if "password:" in line:
                password = line.split("password:")[1].strip()
        if username and password:
            self.passwordReady.emit(username, password)

    def _handle_version_output(self, process: QProcess):
        output = self._read_process_output(process)
        for line in output.splitlines():
            if not line.strip():
                continue
            self.logMessageReady.emit(self._format_log_line(line))
        self.versionReady.emit(output)

    def _handle_2fa_output(self, process: QProcess):
        output = self._read_process_output(process)
        for line in output.splitlines():
            if not line.strip():
                continue
            self.logMessageReady.emit(self._format_log_line(line))
        if "2FA canceled" in output:
            self.twoFactorAuthDisabled.emit()

    # --- 辅助方法 ---

    def _get_common_startup_args(self) -> list[str]:
        """
        从配置中获取通用的启动参数列表。
        这确保了所有需要访问数据目录的命令都使用相同的参数。
        """
        # 如果配置项不存在或为空，返回一个空列表
        return cfg.get(cfg.alistStartupParams) or []

    def _get_data_directory_path(self) -> Optional[Path]:
        """
        根据启动参数确定 Alist 数据目录的路径。
        优先使用 '--data' 参数指定的路径。
        如果未指定，则默认为 Alist 可执行文件所在目录下的 'data' 文件夹。
        """
        # 1. 检查 Alist 工作目录是否已配置
        alist_work_dir = cfg.alistWorkDirectory.value
        if not checkAlistExist(alist_work_dir):
            self.configurationRequired.emit()
            return None

        # 2. 解析启动参数以查找 '--data'
        args = self._get_common_startup_args()
        try:
            # 查找 --data 参数的索引
            data_index = args.index("--data")
            if data_index + 1 < len(args):
                # 获取 --data 后面的路径参数
                data_dir_str = args[data_index + 1]
                return Path(data_dir_str)
            else:
                # --data 参数存在但没有提供路径，这是一个配置错误
                self.operationFailed.emit("启动参数 '--data' 配置错误，缺少路径值。")
                return None
        except ValueError:
            # '--data' 参数不存在，使用默认路径
            # 默认数据目录位于 Alist 可执行文件所在的文件夹内
            return Path(alist_work_dir) / "data"

    def _read_process_output(self, process: QProcess) -> str:
        try:
            return process.readAll().data().decode("utf-8", errors="ignore").strip()
        except Exception as e:
            traceback.print_exc()
            self.errorOccurred.emit(f"读取进程输出时出错: {e}")
            return ""

    def _check_alist_work_directory(self) -> Optional[str]:
        alistWorkDirectory = cfg.alistWorkDirectory.value
        if not checkAlistExist(alistWorkDirectory):
            return None
        return str(getAlistPath(alistWorkDirectory))

    def _format_log_line(self, text: str, level: str = None) -> str:
        text = text.replace("&", "&").replace("<", "<").replace(">", ">")
        text = re.sub(r"\x1b\[[0-9;]*m", "", text)
        log_colors = {
            "ERROR": "#FF4444",
            "WARN": "#FFAA00",
            "WARNING": "#FFAA00",
            "INFO": "#44AAFF",
        }
        if level:
            pattern = r"^"
            replacement = f'<span style="color: {log_colors.get(level, "#FFFFFF")};">{level}: </span>'
            text = re.sub(pattern, replacement, text)
        else:
             for key, color in log_colors.items():
                pattern = r"(\b" + re.escape(key) + r"\b)"
                replacement = f'<span style="color: {color};">{key}</span>'
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text


# 创建服务的单例实例
alistService = AlistService()