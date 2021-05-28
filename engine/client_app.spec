# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['client_app.py'],
             pathex=['D:\\Projects\\work\\user-monitoring-system\\ems-client-app\\engine'],
             binaries=[],
             datas=[],
             hiddenimports=['pynput.mouse._win32', 'pynput.keyboard._win32', 'numpy', 'win32timezone', 'comtypes'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['pyqt5', 'tkinter', 'cryptography'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='client_app',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='client_app')
