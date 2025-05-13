import os
from datetime import datetime
import re

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


def validate_live_url(url: str, silent_mode: bool = False) -> tuple:
    """
    验证直播URL的有效性并自动补充http://前缀
    
    Args:
        url: 需要验证的URL字符串
        silent_mode: 是否为静默模式（纯录屏模式），如果为True则不验证URL
        
    Returns:
        tuple: (processed_url, is_valid, message)
            - processed_url: 处理后的URL（可能添加了http://前缀）
            - is_valid: 布尔值，表示URL是否有效
            - message: 错误消息（如果有的话）
    """
    # 如果是静默模式（纯录屏模式），则不验证URL
    if silent_mode:
        return url, True, ""
        
    # 去除前后空格
    url = url.strip()
    
    # 如果URL为空
    if not url:
        return "", False, "URL不能为空"
    
    # 检查是否有协议前缀，如果没有则添加http://
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    # 简单的URL格式校验
    url_pattern = r'^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$'
    
    # 特定直播平台域名检查
    valid_domains = [
        'douyin.com', 'live.douyin.com',
        'bilibili.com', 'live.bilibili.com',
        'huya.com', 'douyu.com',
        'kuaishou.com', 'live.kuaishou.com'
    ]
    
    # 检查URL格式
    if not re.match(url_pattern, url):
        return url, False, "地址非法，改为纯录屏模式"
    
    # 检查是否是已知直播平台
    domain_found = False
    for domain in valid_domains:
        if domain in url:
            domain_found = True
            break
    
    if not domain_found:
        return url, False, "非已知直播平台，改为纯录屏模式"
    
    return url, True, "" 