import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    'includes': ['tkinter'],
    'include_files': [('output.json', 'output.json')],
}

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

setup(
    name='Electroneek Parser Tool',
    version='1.0',
    description='Electroneek Parser Tool',
    options={'build_exe': build_exe_options},
    executables=[Executable(
        'test_parser_1.py', 
        base=base, 
        target_name='Electroneek Parser Tool.exe', 
        icon='faviconV2.ico'
    )]
)