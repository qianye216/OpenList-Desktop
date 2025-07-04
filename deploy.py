import os
import sys
from app.common.setting import VERSION

if sys.platform == "win32":
    args = [
        'nuitka',
        '--standalone',
        '--windows-disable-console',
        '--plugin-enable=pyside6' ,
        '--include-qt-plugins=sensible,sqldrivers',
        '--assume-yes-for-downloads',
        '--msvc=latest',              # Use MSVC
        # '--mingw64',                    # Use MinGW
        '--show-memory' ,
        '--show-progress' ,
        '--windows-icon-from-ico=app/resource/images/logo.ico',
        '--windows-product-name="OpenList-Desktop"',
        f'--windows-file-version={VERSION}',
        f'--windows-product-version={VERSION}',
        '--windows-file-description="OpenList-Desktop"',
        '--output-dir=dist',
        'OpenList-Desktop.py',
    ]
elif sys.platform == "darwin":
    args = [
        'python3 -m nuitka',
        '--standalone',
        '--plugin-enable=pyside6',
        '--include-qt-plugins=sensible,sqldrivers',
        '--show-memory',
        '--show-progress',
        "--macos-create-app-bundle",
        "--assume-yes-for-download",
        "--macos-disable-console",
        f"--macos-app-version={VERSION}",
        "--macos-app-name=OpenList-Desktop",
        "--macos-app-icon=app/resource/images/logo.icns",
        "--copyright=qianye",
        '--output-dir=dist',
        'OpenList-Desktop.py',
    ]
else:
    args = [
        'pyinstaller',
        '-w',
        'OpenList-Desktop.py',
    ]


os.system(' '.join(args))