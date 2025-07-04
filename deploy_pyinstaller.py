'''
Author: qianye
Date: 2025-07-04 18:30:41
LastEditTime: 2025-07-04 21:40:09
Description: 
'''
import os
import sys
from app.common.setting import VERSION

def build_with_pyinstaller():
    """
    使用PyInstaller打包应用程序
    支持Windows和macOS平台
    """
    
    # 通用参数
    common_args = [
        'pyinstaller',
        '--onedir',          # 创建单目录分发
        '--windowed',        # 无控制台窗口
        '--clean',           # 清理临时文件
        '--noconfirm',       # 覆盖输出目录而不确认
        '--distpath=dist',   # 输出目录
        '--workpath=build',  # 工作目录
        '--specpath=.',      # spec文件路径
        '--name=OpenList-Desktop', # 应用程序名称
    ]
    
    # 添加隐藏导入
    hidden_imports = [
        '--hidden-import=PySide6.QtCore',
        '--hidden-import=PySide6.QtGui', 
        '--hidden-import=PySide6.QtWidgets',
        '--hidden-import=PySide6.QtSql',
    ]
    
    # 使用 os.pathsep 作为正确的分隔符 (Windows: ';', macOS/Linux: ':')
    # 这使得脚本更具可移植性
    separator = os.pathsep

    # 添加数据文件，确保所有必要的资源都被包含
    # PyInstaller会处理将这些文件/目录复制到正确的位置
    data_files = [
        f'--add-data=tools{separator}tools',
    ]
    
    if sys.platform == "win32":
        # Windows特定参数
        platform_args = [
            '--icon=app/resource/images/logo.ico',  # Windows图标
        ]
        
    elif sys.platform == "darwin":
        # macOS特定参数
        platform_args = [
            '--icon=app/resource/images/logo.icns',  # macOS图标
            '--osx-bundle-identifier=com.qianye.openlist-desktop',  # Bundle标识符
        ]
        
    else:
        # Linux或其他平台
        platform_args = [
            '--icon=app/resource/images/logo.png',
        ]
    
    # 组合所有参数
    args = common_args + hidden_imports + data_files + platform_args + ['OpenList-Desktop.py']
    
    print("Building application with PyInstaller...")
    print(f"Platform: {sys.platform}")
    print(f"Version: {VERSION}")
    print(f"Command: {' '.join(args)}")
    
    # 执行打包命令
    result = os.system(' '.join(args))
    
    if result == 0:
        print("\nBuild successful!")
        if sys.platform == "darwin":
            # macOS .app 的可执行文件需要手动添加执行权限
            executable_path = "dist/OpenList-Desktop.app/Contents/MacOS/OpenList-Desktop"
            print(f"Adding execute permissions to {executable_path}")
            os.chmod(executable_path, 0o755)
            print("macOS app bundle: dist/OpenList-Desktop.app")
        elif sys.platform == "win32":
            print("Windows executable: dist/OpenList-Desktop/OpenList-Desktop.exe")
    else:
        print(f"\nBuild failed with exit code: {result}")
        sys.exit(1)

if __name__ == "__main__":
    build_with_pyinstaller()