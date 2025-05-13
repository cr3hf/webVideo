import sys
import os
from utils.logger import init_logger
from config.config_manager import load_config
from scheduler.task_scheduler import setup_scheduler
from gui.main_window import start_gui

def main():
    # 初始化日志
    try:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        # 确保日志目录存在
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except Exception:
                # 如果无法创建日志目录，使用当前目录
                log_dir = '.'
        # 启动时清空日志文件
        init_logger(log_dir, clean_logs=True)
    except Exception as e:
        print(f"初始化日志时出错: {e}")
        # 如果初始化日志失败，继续运行但不记录日志
        pass
    
    # 加载配置
    config = load_config()
    
    # 创建调度器
    scheduler = setup_scheduler(config)
    
    # 启动GUI（将调度器传递给GUI）
    start_gui(config, scheduler)
    
    # GUI关闭后，关闭调度器
    scheduler.shutdown()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序发生异常: {e}") 