import os
import json
from typing import Dict, Any

def get_user_config_path():
    # 获取用户根目录下的config.json
    return os.path.join(os.path.expanduser("~"), "config.json")

# 默认配置（可根据实际需求调整）
def get_default_config():
    return {
        "douyin_url": "https://live.douyin.com/547977714661",
        "start_time": "2030-12-30 20:00:00",
        "duration_minutes": 60,
        "save_path": "./videos",
        "video_format": "mkv",
        "video_codec": "h264",
        "resolution": "window",
        "monitor_index": 0,
        "audio_device": "无音频",
        "framerate": "15",
        "record_quality": "中",
        "silent_mode": False,
        "enable_fullscreen": True,
        "enable_unmute": True,
        "enable_browser_fullscreen": False,
        "enable_bilibili_fullscreen": False,
        "custom_key1_enabled": False,
        "custom_key1": "",
        "custom_key2_enabled": False,
        "custom_key2": "",
        "enable_recurring": False,
        "recurring_days": {
            "monday": False,
            "tuesday": False,
            "wednesday": False,
            "thursday": False,
            "friday": False,
            "saturday": False,
            "sunday": False,
            "everyday": False
        }
    }

def load_config():
    config_path = get_user_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # 不存在或读取失败，写入默认配置
    config = get_default_config()
    save_config(config)
    return config

def save_config(config):
    config_path = get_user_config_path()
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("保存配置失败：", e)

def validate_config(config: Dict[str, Any]) -> bool:
    # 简单校验，后续可扩展
    required_keys = get_default_config().keys()
    for key in required_keys:
        if key not in config:
            return False
    return True 