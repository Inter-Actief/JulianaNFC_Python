# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import copy_metadata

block_cipher = None

data = [('resources', 'resources')]
data.extend(copy_metadata("tendo"))  # To include tendo requirement - https://github.com/pycontribs/tendo/issues/29

hidden_imports = ['threading', 'time', 'queue', 'werkzeug', 'tendo']
hidden_imports += collect_submodules('nfc')

a = Analysis(['juliana.py'],
             pathex=['.'],
             binaries=[],
             datas=data,
             hiddenimports=hidden_imports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='JulianaNFC',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon='resources/main.ico')
