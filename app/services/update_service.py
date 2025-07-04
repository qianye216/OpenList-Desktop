# coding: utf-8
"""
Author: qianye
Date: 2025-04-05 10:16:15
LastEditTime: 2025-06-26 10:00:00
Description: Refactored update checking service.
"""

import enum
import platform
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional

import httpx
from PySide6.QtCore import QVersionNumber

from ..common.config import cfg
from ..common.exception_handler import exceptionHandler
from ..common.setting import OPENLIST_UPDATE_URL, RCLONE_UPDATE_URL, UPDATE_URL
from ..common.utils import getSystemProxy


class RateLimitExceededException(Exception):
    """速率限制异常"""

    def __init__(self, message="API请求次数已达上限，请稍后再试"):
        self.message = message
        super().__init__(self.message)


# 1. 新增一个数据类来表示单个附件
@dataclass
class ReleaseAsset:
    """
    存储发布版本中单个附件（asset）的信息

    Attributes
    ----------
    name : str
        附件文件名
    size: int
        附件大小 (bytes)
    download_url : str
        附件的下载链接
    created_at : str
        附件创建时间的 ISO 8601 格式字符串
    """

    name: str
    size: int
    download_url: str
    created_at: str


# 2. 修改 UpdateInfo 数据类，添加一个附件列表
@dataclass
class UpdateInfo:
    """
    存储版本更新信息的完整数据类

    Attributes
    ----------
    version : str
        最新版本号
    changelog : str
        更新日志
    assets: List[ReleaseAsset]
        附件列表
    """

    version: str
    changelog: str
    assets: List[ReleaseAsset] = field(default_factory=list)


class UpdateTarget(enum.Enum):
    """
    定义更新检查的目标

    每个成员的值是一个元组，包含:
    - API URL
    - 用于异常日志的键名
    - 是否需要 GitHub Token 进行认证
    """

    MAIN_APP = (UPDATE_URL, "version", True)
    ALIST = (OPENLIST_UPDATE_URL, "alist_version", True)
    RCLONE = (RCLONE_UPDATE_URL, "rclone_version", True)

    @property
    def url(self) -> str:
        return self.value[0]

    @property
    def log_key(self) -> str:
        return self.value[1]

    @property
    def needs_auth(self) -> bool:
        return self.value[2]


class UpdateService:
    """
    一个统一的版本更新检查服务
    """

    def __init__(self):
        self.version_pattern = re.compile(r"v(\d+\.\d+\.\d+)")

    def _get_system_info(self):
        """
        获取当前系统和架构的关键字映射。

        Returns
        -------
        tuple[list, list]
            返回一个元组，分别包含操作系统关键字列表和架构关键字列表。
        """
        # 操作系统关键字映射
        os_map = {
            "win32": ["win", "windows"],
            "linux": ["linux"],
            "darwin": ["mac", "darwin", "osx"],
        }

        # 架构关键字映射 (规范化为通用名称)
        machine = platform.machine().lower()
        arch_map = {
            "x86_64": ["amd64", "x64", "x86_64"],
            "amd64": ["amd64", "x64", "x86_64"],  # `platform.machine()` on Windows
            "i386": ["386", "x86", "ia32"],
            "x86": ["386", "x86", "ia32"],
            "arm64": ["arm64", "aarch64"],
            "aarch64": ["arm64", "aarch64"],
        }

        os_keywords = os_map.get(sys.platform, [])
        arch_keywords = arch_map.get(machine, [])

        return os_keywords, arch_keywords

    def _filter_assets_for_current_system(
        self, all_assets: List[ReleaseAsset]
    ) -> List[ReleaseAsset]:
        """
        根据当前系统和架构筛选附件列表。

        Parameters
        ----------
        all_assets : List[ReleaseAsset]
            从API获取的全部附件列表。

        Returns
        -------
        List[ReleaseAsset]
            筛选后只包含匹配当前系统附件的列表。
        """
        os_keywords, arch_keywords = self._get_system_info()

        if not os_keywords or not arch_keywords:
            # 如果无法确定系统或架构，为安全起见返回所有附件
            return all_assets

        filtered_assets = []
        for asset in all_assets:
            asset_name_lower = asset.name.lower()

            # 检查文件名是否同时包含系统和架构的关键字
            has_os_keyword = any(key in asset_name_lower for key in os_keywords)
            has_arch_keyword = any(key in asset_name_lower for key in arch_keywords)

            if has_os_keyword and has_arch_keyword:
                filtered_assets.append(asset)

        # 如果经过严格筛选后一个都没匹配上，可能是命名不规范，放宽条件只匹配系统
        if not filtered_assets:
            for asset in all_assets:
                asset_name_lower = asset.name.lower()
                if any(key in asset_name_lower for key in os_keywords):
                    filtered_assets.append(asset)

        # 如果还是一个都没有，返回全部让用户自己选
        if not filtered_assets:
            return all_assets

        return filtered_assets

    def _check_rate_limit(self, response: httpx.Response):
        """
        检查API速率限制

        Raises
        ------
        RateLimitExceededException
            当速率限制剩余次数为0时抛出异常
        """
        rate_limit_remaining = response.headers.get("x-ratelimit-remaining")
        if rate_limit_remaining is not None:
            try:
                if int(rate_limit_remaining) == 0:
                    reset_time = response.headers.get("x-ratelimit-reset", "")
                    message = "API请求次数已达上限，请稍后再试"
                    if reset_time:
                        # 可以将时间戳转换为更易读的格式
                        # from datetime import datetime, timezone
                        # reset_dt = datetime.fromtimestamp(int(reset_time), tz=timezone.utc)
                        # message += f"（重置时间: {reset_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}）"
                        message += f" (Reset Timestamp: {reset_time})"
                    raise RateLimitExceededException(message)
            except (ValueError, TypeError):
                # 如果无法解析剩余次数，忽略检查
                pass

    def _fetch_latest_release_info(self, target: UpdateTarget) -> Optional[UpdateInfo]:
        """
        从GitHub API获取最新的发布信息

        Parameters
        ----------
        target : UpdateTarget
            要检查的目标

        Returns
        -------
        UpdateInfo | None
            成功时返回包含版本信息的UpdateInfo对象，失败时返回None
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.64",
            "Accept": "application/vnd.github.v3+json",
        }

        # 如果目标需要认证，则添加GitHub Token
        if target.needs_auth:
            github_token = cfg.get(cfg.githubToken)
            if github_token:
                headers["Authorization"] = f"token {github_token}"

        proxy = getSystemProxy()

        try:
            with httpx.Client(proxy=proxy, follow_redirects=True, timeout=5) as client:
                response = client.get(target.url, headers=headers)

                self._check_rate_limit(response)
                response.raise_for_status()

                data = response.json()

                version_tag = data.get("tag_name")
                if not version_tag:
                    return None

                # 使用更通用的方式处理版本号前缀'v'
                latest_version = version_tag.lstrip("v")

                if QVersionNumber.fromString(latest_version).isNull():
                    return None

                changelog = data.get("body", "No changelog provided.")

                # 3. 解析附件信息
                assets_list = []
                github_proxy = cfg.get(cfg.githubProxy)

                for asset_data in data.get("assets", []):
                    # 确保关键信息存在
                    if all(
                        k in asset_data
                        for k in ["name", "size", "browser_download_url", "created_at"]
                    ):
                        download_url = asset_data["browser_download_url"]
                        # 如果设置了代理，则拼接代理地址
                        if github_proxy:
                            download_url = f"{github_proxy.rstrip('/')}/{download_url}"

                        asset = ReleaseAsset(
                            name=asset_data["name"],
                            size=asset_data["size"],
                            download_url=download_url,
                            created_at=asset_data["created_at"],
                        )
                        assets_list.append(asset)

                # 调用新的过滤方法
                filtered_assets = self._filter_assets_for_current_system(assets_list)

                return UpdateInfo(
                    version=latest_version, changelog=changelog, assets=filtered_assets
                )

        except httpx.HTTPStatusError as e:
            print(
                f"HTTP error occurred while checking {target.name}: {e.response.status_code} - {e.response.text}"
            )
        except RateLimitExceededException as e:
            print(f"Rate limit exceeded for {target.name}: {e.message}")
            # 可以重新抛出，让上层UI捕获并显示给用户
            raise e
        except Exception as e:
            # 捕获其他所有异常（网络问题、JSON解析错误等）
            print(f"An unexpected error occurred while checking {target.name}: {e}")

        return None

    def check_for_updates(
        self, target: UpdateTarget, current_version: Optional[str] = None
    ) -> Optional[UpdateInfo]:
        """
        检查指定目标的更新

        Parameters
        ----------
        target : UpdateTarget
            要检查的目标（如：MAIN_APP, ALIST, RCLONE）
        current_version : str, optional
            要进行比较的当前版本号。如果提供，则仅在发现新版本时返回信息。
            如果为None，则总是返回获取到的最新版本信息。

        Returns
        -------
        UpdateInfo | None
            - 如果找到更新（或未提供current_version），返回UpdateInfo对象。
            - 如果没有新版本或发生错误，返回None。
        """
        current_version = current_version.lstrip("v") if current_version else ""

        # 使用装饰器模式的思想，但直接在函数内部调用以动态传入log_key
        @exceptionHandler(target.log_key, None)
        def _check():
            release_info = self._fetch_latest_release_info(target)
            if not release_info:
                return None

            # 如果没有提供当前版本，直接返回最新信息
            if current_version is None:
                return release_info

            # 如果提供了当前版本，则进行比较
            latest_version_num = QVersionNumber.fromString(release_info.version)
            current_version_num = QVersionNumber.fromString(current_version)

            if latest_version_num > current_version_num:
                return release_info

            return None

        return _check()


update_service = UpdateService()
