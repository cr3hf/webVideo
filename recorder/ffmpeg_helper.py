import os
from screeninfo import get_monitors
import subprocess
import re
import sys

def get_system_resolution():
    """获取系统所有显示器的分辨率信息"""
    displays = []
    try:
        # 尝试使用screeninfo库
        monitors = get_monitors()
        # 从左到右排序显示器
        monitors = sorted(monitors, key=lambda m: m.x)
        for m in monitors:
            displays.append({
                'x': m.x,
                'y': m.y,
                'width': m.width,
                'height': m.height
            })
    except Exception:
        # 如果screeninfo失败，尝试使用PowerShell（Windows专用）
        try:
            cmd = "powershell \"Get-WmiObject -Class Win32_VideoController | Select-Object CurrentHorizontalResolution, CurrentVerticalResolution\""
            result = subprocess.check_output(cmd, shell=True).decode('utf-8')
            
            # 解析PowerShell输出
            matches = re.findall(r'(\d+)\s+(\d+)', result)
            if matches:
                # 假设第一个是主显示器
                displays.append({
                    'x': 0,
                    'y': 0,
                    'width': int(matches[0][0]),
                    'height': int(matches[0][1])
                })
                
                # 如果有第二个显示器，假设在右侧
                if len(matches) > 1:
                    first_width = int(matches[0][0])
                    displays.append({
                        'x': first_width,
                        'y': 0,
                        'width': int(matches[1][0]),
                        'height': int(matches[1][1])
                    })
        except Exception:
            pass

    # 如果以上方法都失败，提供默认值
    if not displays:
        displays = [
            {'x': 0, 'y': 0, 'width': 1920, 'height': 1080},  # 默认主显示器
            {'x': 1920, 'y': 0, 'width': 1920, 'height': 1080}  # 默认第二显示器
        ]
    
    return displays

# 在模块加载时获取一次系统分辨率，避免重复调用
SYSTEM_DISPLAYS = get_system_resolution()

def get_monitor_geometry(monitor_index=0):
    """获取指定显示器的几何信息"""
    try:
        # 先尝试实时获取（确保数据准确）
        monitors = get_monitors()
        # 从左到右排序显示器
        monitors = sorted(monitors, key=lambda m: m.x)
        if 0 <= monitor_index < len(monitors):
            m = monitors[monitor_index]
            return m.x, m.y, m.width, m.height
    except Exception:
        pass
    
    # 如果无法实时获取，使用模块加载时缓存的显示器信息
    if 0 <= monitor_index < len(SYSTEM_DISPLAYS):
        display = SYSTEM_DISPLAYS[monitor_index]
        return display['x'], display['y'], display['width'], display['height']
    
    # 缓存中也没有对应显示器，使用默认值
    if monitor_index == 0:  # 主显示器
        return 0, 0, 1920, 1080
    else:  # 假设第二显示器在右侧
        return 1920, 0, 1920, 1080

def get_ffmpeg_path():
    """自动获取ffmpeg可执行文件路径，支持打包和开发环境"""
    if hasattr(sys, '_MEIPASS'):
        ffmpeg_dir = os.path.join(sys._MEIPASS, 'ffmpeg', 'bin')
    else:
        ffmpeg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ffmpeg', 'bin'))
    ffmpeg_exe = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
    return ffmpeg_exe

def generate_ffmpeg_cmd(config: dict, output_file: str) -> list:
    # 根据选择的显示器设置偏移量和分辨率
    monitor_index = config.get('monitor_index', 0)
    offset_x, offset_y, capture_width, capture_height = get_monitor_geometry(monitor_index)
    
    # 获取用户设置的帧率
    framerate = config.get('framerate', '25')
    
    # 基本命令：始终以显示器的原始分辨率进行捕获
    cmd = [
        get_ffmpeg_path(),
        '-y',
        '-f', 'gdigrab',
        '-framerate', framerate,
        '-offset_x', str(offset_x),
        '-offset_y', str(offset_y),
        '-video_size', f"{capture_width}x{capture_height}",
        '-i', 'desktop',
    ]

    # 添加音频设备（如果指定）
    audio_device = config.get('audio_device', '无音频')
    if audio_device and audio_device != '无音频':
        cmd += [
            '-f', 'dshow',
            '-i', f'audio={audio_device}',
            '-c:a', 'aac',
            '-b:a', '128k',
        ]
    
    # 如果用户指定了分辨率且不是'window'，添加缩放滤镜
    output_width, output_height = capture_width, capture_height  # 默认使用捕获分辨率
    if config.get('resolution') != 'window' and 'x' in config.get('resolution', ''):
        output_width, output_height = map(int, config.get('resolution').split('x'))
        # 添加缩放滤镜
        cmd += [
            '-vf', f'scale={output_width}:{output_height}',
        ]
        
    # 根据质量设置视频编码参数
    quality = config.get('record_quality', '中')
    video_codec = config.get('video_codec', 'h264')
    
    # 设置各编码器在不同质量下的参数
    # 使用CRF模式(恒定质量)而非固定码率，画质更均衡
    if video_codec == 'h264':
        if quality == '高':
            # 高质量：画质优先，适合后期剪辑
            preset = 'medium'
            cmd += [
                '-c:v', 'libx264',
                '-crf', '18',  # 较低的CRF值 = 更高画质
                '-preset', preset,
                '-pix_fmt', 'yuv420p',
            ]
        elif quality == '低':
            # 低质量：极致压缩，适合长时间录制
            preset = 'veryfast'
            cmd += [
                '-c:v', 'libx264',
                '-crf', '32',  # 较高的CRF值 = 更小文件
                '-preset', preset,
                '-pix_fmt', 'yuv420p',
            ]
        else:  # 中等质量(默认)
            # 平衡画质和体积
            preset = 'veryfast'
            cmd += [
                '-c:v', 'libx264',
                '-crf', '25',
                '-preset', preset,
                '-pix_fmt', 'yuv420p',
            ]
    elif video_codec == 'h265':  # HEVC能以更低码率实现相似画质
        if quality == '高':
            preset = 'medium'
            cmd += [
                '-c:v', 'libx265',
                '-crf', '20',  # H265的CRF值比H264低6左右相当于同等画质
                '-preset', preset,
                '-pix_fmt', 'yuv420p',
                '-tag:v', 'hvc1',  # 增加兼容性
            ]
        elif quality == '低':
            preset = 'veryfast'
            cmd += [
                '-c:v', 'libx265',
                '-crf', '36',
                '-preset', preset,
                '-pix_fmt', 'yuv420p',
                '-tag:v', 'hvc1',
            ]
        else:  # 中等质量
            preset = 'veryfast'
            cmd += [
                '-c:v', 'libx265',
                '-crf', '28',
                '-preset', preset,
                '-pix_fmt', 'yuv420p',
                '-tag:v', 'hvc1',
            ]
    elif video_codec == 'vp9':  # VP9使用CQ模式，类似CRF
        if quality == '高':
            speed = '1'
            cmd += [
                '-c:v', 'libvpx-vp9',
                '-crf', '19',  # VP9的CRF范围不同，但大致相当
                '-b:v', '0',   # CRF模式需要设置码率为0
                '-speed', speed,
                '-row-mt', '1',  # 多线程编码
                '-pix_fmt', 'yuv420p',
            ]
        elif quality == '低':
            speed = '4'
            cmd += [
                '-c:v', 'libvpx-vp9',
                '-crf', '37',
                '-b:v', '0',
                '-speed', speed,
                '-row-mt', '1',
                '-pix_fmt', 'yuv420p',
            ]
        else:  # 中等质量
            speed = '2'
            cmd += [
                '-c:v', 'libvpx-vp9',
                '-crf', '28',
                '-b:v', '0',
                '-speed', speed,
                '-row-mt', '1',
                '-pix_fmt', 'yuv420p',
            ]
    elif video_codec == 'av1':  # AV1也支持CRF
        if quality == '高':
            cpu_used = '3'
            cmd += [
                '-c:v', 'libaom-av1',
                '-crf', '20',
                '-b:v', '0',
                '-cpu-used', cpu_used,
                '-pix_fmt', 'yuv420p',
            ]
        elif quality == '低':
            cpu_used = '8'
            cmd += [
                '-c:v', 'libaom-av1',
                '-crf', '38',
                '-b:v', '0',
                '-cpu-used', cpu_used,
                '-pix_fmt', 'yuv420p',
            ]
        else:  # 中等质量
            cpu_used = '5'
            cmd += [
                '-c:v', 'libaom-av1',
                '-crf', '29',
                '-b:v', '0',
                '-cpu-used', cpu_used,
                '-pix_fmt', 'yuv420p',
            ]
    else:  # 默认回退到h264
        preset = 'veryfast'
        cmd += [
            '-c:v', 'libx264',
            '-crf', '25',  # 默认中等质量
            '-preset', preset,
            '-pix_fmt', 'yuv420p',
        ]
    
    # 添加输出文件
    cmd.append(output_file)
    return cmd 