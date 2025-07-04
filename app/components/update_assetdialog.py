'''
Author: qianye
Date: 2025-06-30 21:33:17
LastEditTime: 2025-07-03 21:59:58
Description: 
'''
# coding:utf-8
import os

import httpx
from PySide6.QtCore import QDateTime, QStandardPaths, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    FluentIcon,
    FluentStyleSheet,
    InfoBar,
    InfoBarPosition,
    MaskDialogBase,
    ProgressBar,
    ScrollArea,
    SubtitleLabel,
    TransparentToolButton,
)

from ..common.concurrent import TaskExecutor
from ..common.utils import getSystemProxy, openLocalFile

# 使用相对导入
from ..services.update_service import ReleaseAsset, UpdateInfo


def format_size(size_bytes: int) -> str:
    """将字节大小格式化为可读的字符串 (KB, MB, GB)"""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"


class AssetCard(CardWidget):
    """
    显示单个附件信息卡片，继承自 CardWidget
    - 支持显示进度条
    - 点击下载按钮会弹出文件保存对话框
    """
    # 信号：(附件对象, 本地保存路径)
    downloadStarted = Signal(ReleaseAsset, str)
    # 添加进度更新信号
    progressUpdated = Signal(int, str)  # (进度百分比, 格式化文本)

    def __init__(self, asset: ReleaseAsset, install_path:None = None, parent=None):
        super().__init__(parent=parent)
        self.asset = asset
        self.install_path = install_path or QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        
        # 连接进度更新信号到槽函数
        self.progressUpdated.connect(self._update_progress_ui)

        self._init_widget()
        self._init_layout()

    def _init_widget(self):
        """初始化小部件属性"""
        self.iconButton = TransparentToolButton(FluentIcon.DOCUMENT, self)
        self.nameLabel = BodyLabel(self.asset.name, self)
        self.infoLabel = CaptionLabel(self)
        self.downloadButton = TransparentToolButton(FluentIcon.DOWNLOAD, self)
        self.progressBar = ProgressBar(self)

        self.iconButton.setFixedSize(36, 36)
        self.iconButton.setEnabled(False)

        self.downloadButton.setFixedSize(36, 36)
        self.downloadButton.clicked.connect(self._on_download_clicked)
        
        self.progressBar.setHidden(True) # 默认隐藏进度条
        self.progressBar.setTextVisible(True)
        self.progressBar.setRange(0, 100)

        size_str = format_size(self.asset.size)
        created_dt = QDateTime.fromString(self.asset.created_at, Qt.DateFormat.ISODate)
        date_str = created_dt.toString("yyyy-MM-dd hh:mm")
        self.infoLabel.setText(f"{size_str} • {date_str}")

    def _init_layout(self):
        """初始化布局"""
        self.hLayout = QHBoxLayout()
        self.vLayout = QVBoxLayout(self) # 主布局
        self.infoLayout = QVBoxLayout()

        self.hLayout.setContentsMargins(12, 12, 12, 8)
        self.hLayout.setSpacing(12)
        self.infoLayout.setSpacing(2)
        
        self.hLayout.addWidget(self.iconButton)

        self.infoLayout.addWidget(self.nameLabel)
        self.infoLayout.addWidget(self.infoLabel)
        self.hLayout.addLayout(self.infoLayout, 1)

        self.hLayout.addWidget(self.downloadButton)
        
        self.vLayout.addLayout(self.hLayout)
        self.vLayout.addWidget(self.progressBar)
        self.vLayout.setContentsMargins(0, 0, 0, 8)

    def _on_download_clicked(self):
        """处理下载按钮点击事件，弹出文件保存对话框"""

            
        default_path = os.path.join(self.install_path, self.asset.name)
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", default_path, "All Files (*)"
        )
    
        if save_path:
            # 保存文件路径到实例变量，供下载完成后使用
            self.current_save_path = save_path
            
            self.downloadButton.setEnabled(False)
            self.downloadButton.setIcon(FluentIcon.SYNC)
            self.progressBar.setValue(0)
            self.progressBar.setHidden(False)
            # 使用TaskExecutor执行异步下载
            TaskExecutor.runTask(self._download_file, self.asset.download_url, save_path).then(
                lambda result: self._on_download_finished(result["success"], result["message"])
            )
    
    def _download_file(self, url: str, save_path: str) -> dict:
        """执行文件下载的异步任务函数"""
        try:
            proxy = getSystemProxy()
            with httpx.stream("GET", url, timeout=30, follow_redirects=True, proxy=proxy) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                with open(save_path, 'wb') as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 使用信号更新进度条
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            format_text = f"{self._format_size(downloaded_size)} / {self._format_size(total_size)}"
                            # 发射信号更新进度条
                            self.progressUpdated.emit(progress, format_text)
            
            if downloaded_size == total_size or total_size == 0:
                return {"success": True, "message": "下载完成"}
            else:
                return {"success": False, "message": "文件不完整"}

        except Exception as e:
            return {"success": False, "message": f"下载失败: {e}"}
    
    def _update_progress_ui(self, progress: int, format_text: str):
        """更新进度条UI的槽函数"""
        self.progressBar.setValue(progress)
        self.progressBar.setFormat(format_text)
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小显示"""
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = 0
        while size_bytes >= 1024 and i < len(size_name) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.2f} {size_name[i]}"
    
    def _on_download_finished(self, success: bool, message: str):
        """下载完成后的处理"""
        self.progressBar.setHidden(True)
        if success:
            self.downloadButton.setIcon(FluentIcon.COMPLETED)
            # 下载成功后按钮保持禁用和完成状态
            
            # 下载成功后打开文件所在路径
            if hasattr(self, 'current_save_path') and self.current_save_path:
                try:
                    openLocalFile(self.current_save_path)
                except Exception as e:
                    # 如果打开文件路径失败，显示提示信息但不影响下载完成状态
                    InfoBar.warning(
                        "提示",
                        f"文件下载成功，但无法打开文件所在路径: {e}",
                        duration=3000,
                        parent=self.window(),
                        position=InfoBarPosition.TOP
                    )
        else:
            self.downloadButton.setEnabled(True)
            self.downloadButton.setIcon(FluentIcon.DOWNLOAD)
            # 在父窗口显示错误信息
            InfoBar.error(
                "下载失败",
                message,
                duration=3000,
                parent=self.window(),
                position=InfoBarPosition.TOP
            )
    


class UpdateAssetsDialog(MaskDialogBase):
    """显示更新附件列表的对话框"""
    # 信号 (附件对象, 本地保存路径)
    startDownload = Signal(ReleaseAsset, str)

    def __init__(self, update_info: UpdateInfo, install_path: None, parent=None):
        super().__init__(parent=parent)
        self.update_info = update_info
        self.install_path = install_path
        self.asset_cards = {}  # 存储附件卡片实例 {asset_name: card_widget}
        self.download_threads = {} # 存储下载线程

        self._init_widget()
        self._init_layout()
        
        FluentStyleSheet.DIALOG.apply(self.widget)
        
        self.populate_assets()

    def _init_widget(self):
        """初始化对话框窗口小部件"""
        self.titleLabel = SubtitleLabel("选择要下载的更新软件包", self.widget)
        self.pathLabel = BodyLabel(f"将下载到目录: {self.install_path}", self.widget)
        self.pathLabel.setWordWrap(True)
        
        # 添加关闭按钮
        self.closeButton = TransparentToolButton(FluentIcon.CLOSE, self.widget)
        self.closeButton.setFixedSize(32, 32)
        self.closeButton.clicked.connect(self.close)
        
        self.scrollArea = ScrollArea(self.widget)
        self.scrollWidget = QWidget()
    
        self.widget.setObjectName("centerWidget")
        self.widget.setMaximumHeight(480)
        self.widget.setMaximumWidth(640)
        
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.enableTransparentBackground()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setObjectName("scrollArea")
        self.setShadowEffect(60, (0, 6), QColor(0, 0, 0, 50))
        self.setMaskColor(QColor(0, 0, 0, 76))
        
    def _init_layout(self):
        """初始化对话框布局"""
        self.assetLayout = QVBoxLayout(self.scrollWidget)
        self.mainLayout = QVBoxLayout(self.widget)
        
        # 创建标题栏水平布局
        self.titleLayout = QHBoxLayout()
        self.titleLayout.addWidget(self.titleLabel)
        self.titleLayout.addStretch()  # 添加弹性空间
        self.titleLayout.addWidget(self.closeButton)
        self.titleLayout.setContentsMargins(0, 0, 0, 0)
    
        self.mainLayout.setContentsMargins(24, 24, 24, 24)
        self.mainLayout.setSpacing(8)
        self.mainLayout.addLayout(self.titleLayout)  # 添加标题栏布局
        self.mainLayout.addWidget(self.pathLabel)
        self.mainLayout.addSpacing(10)
        self.mainLayout.addWidget(self.scrollArea)
    
        self.assetLayout.setContentsMargins(0, 0, 0, 0)
        self.assetLayout.setSpacing(8)
        self.assetLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

    def populate_assets(self):
        """用附件信息填充滚动区域"""
        if not self.update_info.assets:
            no_assets_label = BodyLabel("未找到可用的更新文件。", self.scrollWidget)
            no_assets_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.assetLayout.addWidget(no_assets_label)
            return

        for asset in self.update_info.assets:
            card = AssetCard(asset, self.install_path, self.scrollWidget)
            self.assetLayout.addWidget(card)




