import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from recorder.recorder import recorder_instance
from browser.browser_controller import browser_controller_instance
from browser.clicker import Clicker

class TaskScheduler:
    def __init__(self, config):
        self.config = config
        self.scheduler = BackgroundScheduler()
        self.clicker = None
        self.main_window = None
        self.logger = logging.getLogger(__name__)
        self.current_job_id = 'start_record'
        self.current_stop_job_id = 'stop_record'

    def start(self):
        self.scheduler.start()
        self.schedule_recording()

    def set_main_window(self, main_window):
        """设置主窗口引用，用于控制UI状态"""
        self.main_window = main_window

    def schedule_recording(self):
        # 移除可能存在的旧任务
        for job_id in [self.current_job_id, self.current_stop_job_id]:
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass
        
        start_time = datetime.strptime(self.config['start_time'], '%Y-%m-%d %H:%M:%S')
        end_time = start_time + timedelta(minutes=self.config['duration_minutes'])
        
        self.scheduler.add_job(
            self.start_all, 
            'date', 
            run_date=start_time, 
            id=self.current_job_id
        )
        
        self.scheduler.add_job(
            self.stop_all, 
            'date', 
            run_date=end_time, 
            id=self.current_stop_job_id
        )

    def schedule_next_recurring(self):
        """设置下一个循环任务的开始时间"""
        # 如果循环任务未启用，则不进行处理
        if not self.config.get('enable_recurring', False):
            self.logger.info("循环任务未启用，不设置下一个任务")
            return
        
        recurring_days = self.config.get('recurring_days', {})
        self.logger.info(f"当前循环设置: {recurring_days}")
        
        # 获取当前任务的开始时间
        current_start_time = datetime.strptime(self.config['start_time'], '%Y-%m-%d %H:%M:%S')
        self.logger.info(f"当前任务时间: {current_start_time}")
        
        # 计算下一个任务的开始时间
        next_start_time = None
        
        # 处理真实的"每天"设置，这是用户UI上勾选的
        if recurring_days.get('everyday', False):
            # 设置为明天同一时间
            next_start_time = current_start_time + timedelta(days=1)
            self.logger.info(f"设置为每天执行，下一次时间: {next_start_time}")
        else:
            # 重要：使用当前时间（而不是任务开始时间）来计算下一个周期
            # 这样能确保在任务结束后正确计算下一个周期
            now = datetime.now()
            today_weekday = now.weekday()  # 获取当前真实星期几（0-6，其中0是周一）
            self.logger.info(f"当前真实星期几: {today_weekday}")
            
            # 将配置中的星期与weekday值对应起来
            weekday_map = {
                'monday': 0,
                'tuesday': 1,
                'wednesday': 2,
                'thursday': 3,
                'friday': 4,
                'saturday': 5,
                'sunday': 6
            }
            
            # 收集所有启用的星期
            enabled_weekdays = []
            for day, weekday_value in weekday_map.items():
                if recurring_days.get(day, False):
                    enabled_weekdays.append(weekday_value)
            
            self.logger.info(f"启用的星期几: {enabled_weekdays}")
            
            # 如果没有启用任何星期，则不进行循环
            if not enabled_weekdays:
                self.logger.info("没有选择任何星期，不设置循环")
                return
            
            # 排序，以便我们可以找到下一个最近的日期
            enabled_weekdays.sort()
            
            # 找出下一个星期的索引
            next_weekday = None
            for weekday in enabled_weekdays:
                if weekday > today_weekday:
                    next_weekday = weekday
                    break
            
            # 如果没有找到比今天更晚的星期，则回到下一周的第一个启用日
            if next_weekday is None:
                next_weekday = enabled_weekdays[0]
                days_ahead = 7 - today_weekday + next_weekday
                self.logger.info(f"下一个周期在下周，星期几: {next_weekday}，相差天数: {days_ahead}")
            else:
                days_ahead = next_weekday - today_weekday
                self.logger.info(f"下一个周期在本周，星期几: {next_weekday}，相差天数: {days_ahead}")
            
            # 获取当前任务的时间部分（小时、分钟、秒）
            hour = current_start_time.hour
            minute = current_start_time.minute
            second = current_start_time.second
            
            # 计算基准日期（从今天开始）
            base_date = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
            
            # 计算下一个任务的日期
            next_start_time = base_date + timedelta(days=days_ahead)
            self.logger.info(f"计算出的下一个任务时间: {next_start_time}")
        
        # 如果计算出下一个时间，则更新配置并重新调度
        if next_start_time:
            # 将下一次任务时间更新到配置
            next_time_str = next_start_time.strftime('%Y-%m-%d %H:%M:%S')
            self.config['start_time'] = next_time_str
            self.logger.info(f"更新配置中的开始时间为: {next_time_str}")
            
            # 从配置管理器导入配置保存函数，确保配置被持久化
            from config.config_manager import save_config
            save_config(self.config)
            self.logger.info("配置已保存")
            
            # 生成唯一的任务ID，防止冲突
            current_time = datetime.now().strftime('%Y%m%d%H%M%S')
            self.current_job_id = f'start_record_{current_time}'
            self.current_stop_job_id = f'stop_record_{current_time}'
            self.logger.info(f"生成新的任务ID: {self.current_job_id}")
            
            # 重新调度任务
            self.schedule_recording()
            self.logger.info("已重新调度任务")
            
            # 更新UI中的开始时间并自动启动倒计时
            if hasattr(self, 'main_window') and self.main_window:
                # 直接在主窗口中更新倒计时的起点时间
                self.main_window.start_time = next_start_time
                
                # 先强制更新UI控件，然后再启动倒计时
                from PyQt5.QtCore import QDateTime
                date_time = QDateTime()
                date_time.setSecsSinceEpoch(int(next_start_time.timestamp()))
                self.main_window.start_time_input.setDateTime(date_time)
                self.logger.info("已更新UI中的开始时间")
                
                # 启动倒计时
                self.main_window.start_countdown()
                self.logger.info("已启动新的倒计时")

    def start_all(self):
        # 只发信号，由主线程执行实际操作
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.schedule_start_signal.emit()

    def stop_all(self):
        # 只发信号，由主线程执行实际操作
        self.logger.info("调度器触发stop_all方法")
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.schedule_stop_signal.emit()
            # 不在这里调用schedule_next_recurring，而是在主窗口的on_schedule_stop_record方法中调用

    def shutdown(self):
        self.scheduler.shutdown()


def setup_scheduler(config):
    scheduler = TaskScheduler(config)
    scheduler.start()
    return scheduler 