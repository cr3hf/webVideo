import subprocess
import os
import sys
from threading import Thread
from recorder.ffmpeg_helper import generate_ffmpeg_cmd
from datetime import datetime

class Recorder:
    def __init__(self):
        self.process = None
        self.recording = False
        self.thread = None

    def start_recording(self, config):
        if self.recording:
            return False
        output_dir = config.get('save_path', './videos')
        os.makedirs(output_dir, exist_ok=True)
        safe_time = config.get('start_time', 'record').replace(':', '-').replace(' ', '_')
        filename = f"webVideos_{safe_time}.{config.get('video_format', 'mkv')}"
        output_file = os.path.join(output_dir, filename)
        cmd = generate_ffmpeg_cmd(config, output_file)
        print("[DEBUG] FFmpeg命令：", " ".join(cmd))  # 打印命令
        def run():
            # 设置输出重定向目标
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
                # Windows系统，将输出重定向到NUL设备
                devnull = open('NUL', 'w')
            else:
                # Linux/Mac系统，将输出重定向到/dev/null
                devnull = open('/dev/null', 'w')
                
            try:
                # 直接将FFmpeg的输出重定向到空设备，不创建日志文件
                self.process = subprocess.Popen(
                    cmd, stdout=devnull, stderr=devnull, stdin=subprocess.PIPE,
                    creationflags=creationflags
                )
                self.process.communicate()
            finally:
                # 确保关闭devnull文件句柄
                devnull.close()
                
            self.recording = False
        self.thread = Thread(target=run, daemon=True)
        self.recording = True
        self.thread.start()
        return True

    def stop_recording(self):
        if self.process and self.recording:
            try:
                # 优先尝试向 ffmpeg 发送 'q' 让其优雅退出
                if self.process.stdin:
                    self.process.stdin.write(b'q')
                    self.process.stdin.flush()
                self.process.wait(timeout=5)
            except Exception:
                self.process.terminate()
            self.process = None
            self.recording = False
            return True
        return False

    def is_recording(self):
        return self.recording

recorder_instance = Recorder() 