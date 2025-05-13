import os
import logging
from logging.handlers import RotatingFileHandler

def init_logger(log_dir=None, clean_logs=True):
    """
    初始化日志系统
    
    参数:
        log_dir: 日志目录路径
        clean_logs: 是否清空现有日志文件，默认为True
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # 清除现有的处理器，避免重复添加
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 尝试创建文件处理器
    try:
        if log_dir and log_dir != '.':
            # 确保日志目录存在
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            log_file = os.path.join(log_dir, 'app.log')
            
            # 如果启用了清空日志选项，则清空现有日志文件
            if clean_logs and os.path.exists(log_file):
                try:
                    # 清空日志文件内容
                    open(log_file, 'w').close()
                    logger.info("已清空日志文件")
                except Exception as e:
                    logger.warning(f"清空日志文件失败: {str(e)}")
            
            file_handler = RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            logger.info(f"日志文件位置: {log_file}")
    except Exception as e:
        # 如果创建文件处理器失败，仅使用控制台处理器
        logger.warning(f"无法创建日志文件: {str(e)}")
    
    # 设置第三方库的日志级别
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    
    return logger

def get_logger(name):
    """获取指定名称的logger"""
    return logging.getLogger(name) 