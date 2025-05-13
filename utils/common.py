import os
from datetime import datetime

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def format_time(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def is_valid_path(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        return False


def get_ffmpeg_path():
    import sys, os
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller打包后的临时目录
        return os.path.join(sys._MEIPASS, 'ffmpeg', 'bin', 'ffmpeg.exe')
    else:
        # 开发环境
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(base_dir, '..', 'ffmpeg', 'bin', 'ffmpeg.exe')) 