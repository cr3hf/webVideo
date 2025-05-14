import sys
import subprocess
import re
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton, 
                            QVBoxLayout, QHBoxLayout, QFileDialog, QDateTimeEdit, 
                            QSpinBox, QComboBox, QCheckBox, QMessageBox, QGroupBox,
                            QFormLayout, QTabWidget, QGridLayout)
from PyQt5.QtCore import QDateTime, Qt, QSize, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap
from config.config_manager import save_config
from datetime import datetime, timedelta
from recorder.recorder import recorder_instance
from screeninfo import get_monitors
from browser.browser_controller import browser_controller_instance
from browser.clicker import Clicker
from utils.common import get_ffmpeg_path, validate_live_url
import os
import logging

def get_icon_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'assets', 'icon.ico')
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'icon.ico')

def get_app_version():
    """
    从VERSION.md文件中获取应用版本号
    """
    try:
        # 首先检查当前目录
        version_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'VERSION.md')
        
        # 如果是打包的环境，使用不同的路径
        if hasattr(sys, '_MEIPASS'):
            version_path = os.path.join(sys._MEIPASS, 'VERSION.md')
        
        if os.path.exists(version_path):
            with open(version_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 使用正则表达式匹配版本号
                match = re.search(r'## 版本\s+([\d\.]+)', content)
                if match:
                    return match.group(1)
        return "1.0.0"  # 默认版本号
    except Exception as e:
        logging.error(f"读取版本号出错: {e}")
        return "1.0.0"  # 出错时返回默认版本号

class MainWindow(QWidget):
    schedule_start_signal = pyqtSignal()
    schedule_stop_signal = pyqtSignal()
    def __init__(self, config, scheduler):
        super().__init__()
        self.config = config
        self.scheduler = scheduler
        self.setWindowIcon(QIcon(get_icon_path()))
        
        # 获取应用版本号
        self.app_version = get_app_version()
        
        # 将窗口实例传递给scheduler，以便在录制结束时启用UI控件
        if hasattr(self.scheduler, 'set_main_window'):
            self.scheduler.set_main_window(self)
        
        self.init_ui()
        self.load_config_to_ui()
        
        # 倒计时相关变量
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.original_btn_text = '开始任务'
        self.start_time = None
        self.click_count = 0
        self.click_timer = QTimer(self)
        self.click_timer.timeout.connect(self.reset_click_counter)
        self.click_timer.setSingleShot(True)
        
        # 信号连接
        self.schedule_start_signal.connect(self.on_schedule_start_record)
        self.schedule_stop_signal.connect(self.on_schedule_stop_record)

        # 录制状态标志
        self.is_recording = False

    def init_ui(self):
        # 设置窗口标题，包含版本号
        self.setWindowTitle(f'网页直播录制工具 v{self.app_version}')
        self.setMinimumSize(550, 550)  # 增加最小宽度
        self.setStyleSheet("""
            QWidget {
                font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif;
                font-size: 10pt;
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                margin-top: 12px;
                padding-top: 5px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
                color: #212529;
            }
            
            /* 修复标签背景颜色与整体背景一致 */
            QLabel {
                background-color: transparent;
                padding: 5px 0;
            }
            
            /* 美化下拉列表 - 使用更明显的样式 */
            QComboBox {
                background-color: #f8f9fa;
                border: 1px solid #ced4da;
                padding: 5px 8px;
                min-width: 6em;
                border-radius: 4px;
            }
            QComboBox:hover {
                border-color: #4a86e8;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #ced4da;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #e9ecef;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDEyIDEyIj48cGF0aCBmaWxsPSIjNTU1NTU1IiBkPSJNMSA0aDEwTDYgOSAxIDR6Ii8+PC9zdmc+);
            }
            QComboBox QAbstractItemView {
                selection-background-color: #4a86e8;
                selection-color: white;
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 0px;
                padding: 4px;
            }
            
            /* 美化数字微调按钮 */
            QSpinBox {
                background-color: white;
                padding-right: 20px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: border;
                width: 20px;
                border: none;
                background-color: transparent;
            }
            QSpinBox::up-button {
                subcontrol-position: top right;
                height: 50%;
            }
            QSpinBox::down-button {
                subcontrol-position: bottom right;
                height: 50%;
            }
            QSpinBox::up-arrow {
                image: url(data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24'%3E%3Cpath fill='%23555' d='M7 14l5-5 5 5z'/%3E%3C/svg%3E);
                width: 12px;
                height: 12px;
            }
            QSpinBox::down-arrow {
                image: url(data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24'%3E%3Cpath fill='%23555' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E);
                width: 12px;
                height: 12px;
            }
            
            /* 美化日期时间编辑器 */
            QDateTimeEdit {
                background-color: white;
                padding-right: 20px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px;
            }
            QDateTimeEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: none;
            }
            QDateTimeEdit::down-arrow {
                image: url(data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24'%3E%3Cpath fill='%23555' d='M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z'/%3E%3C/svg%3E);
                width: 16px;
                height: 16px;
            }
            
            /* 美化输入框 */
            QLineEdit {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 8px;
                selection-background-color: #4a86e8;
            }
            
            /* 美化标签和输入框对齐 */
            QFormLayout {
                spacing: 10px;
            }
            
            /* Tab Widget 样式 */
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                border-top-left-radius: 0;
                top: -1px;
                padding: 5px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e0e0e0;
            }
            
            /* 修复复选框样式和对齐 */
            QCheckBox {
                spacing: 8px;
                background-color: transparent;
                min-height: 20px;
                padding: 4px 0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #ced4da;
                border-radius: 2px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #4a86e8;
                border-color: #4a86e8;
                image: url(data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24'%3E%3Cpath fill='white' d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z'/%3E%3C/svg%3E);
            }
            QCheckBox::indicator:unchecked:hover {
                border-color: #4a86e8;
            }
            
            /* 修复静态文本的背景色 */
            QGroupBox QLabel, QTabWidget QLabel, QWidget > QLabel {
                background-color: transparent;
            }
            
            /* 修复表单布局的间距 */
            QFormLayout {
                margin: 5px;
            }
        """)

        # 创建选项卡
        tab_widget = QTabWidget()
        
        # === 基本设置选项卡 ===
        basic_tab = QWidget()
        basic_layout = QVBoxLayout()
        
        # 基本信息组
        basic_group = QGroupBox("直播信息")
        basic_form = QFormLayout()
        basic_form.setContentsMargins(10, 10, 10, 10)  # 设置合适的边距
        basic_form.setHorizontalSpacing(10)  # 横向间距
        basic_form.setVerticalSpacing(10)    # 纵向间距
        basic_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)  # 字段自动扩展
        basic_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 标签左对齐且垂直居中
        
        # 直播地址
        self.url_input = QLineEdit()
        basic_form.addRow("直播网页地址:", self.url_input)
        
        # 时间设置
        time_layout = QHBoxLayout()
        
        # 开始时间
        self.start_time_input = QDateTimeEdit()
        self.start_time_input.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        self.start_time_input.setDateTime(QDateTime.currentDateTime().addSecs(300))  # 默认5分钟后
        self.start_time_input.setMinimumWidth(220)  # 确保足够的宽度显示完整日期时间
        time_layout.addWidget(self.start_time_input, 7)  # 权重为7，占据更多空间
        
        # 录制时长
        self.duration_input = QSpinBox()
        self.duration_input.setRange(1, 1440)
        self.duration_input.setSuffix(" 分钟")
        self.duration_input.setMinimumWidth(80)
        time_layout.addWidget(self.duration_input, 3)  # 权重为3，占据较少空间
        
        basic_form.addRow("开始时间/时长:", time_layout)
        
        # 保存路径
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0)  # 移除内边距
        path_layout.setSpacing(5)  # 减少组件间间距
        
        self.save_path_input = QLineEdit()
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setFixedWidth(80)
        self.browse_btn.clicked.connect(self.choose_save_path)
        
        path_layout.addWidget(self.save_path_input)
        path_layout.addWidget(self.browse_btn)
        
        basic_form.addRow("保存路径:", path_layout)
        
        basic_group.setLayout(basic_form)
        basic_layout.addWidget(basic_group)
        
        # 录制设置组
        record_group = QGroupBox("录制设置")
        record_form = QFormLayout()
        record_form.setContentsMargins(10, 10, 10, 10)  # 设置合适的边距
        record_form.setHorizontalSpacing(10)  # 横向间距
        record_form.setVerticalSpacing(10)    # 纵向间距
        record_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)  # 字段自动扩展
        record_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 标签左对齐且垂直居中
        
        # 视频格式
        self.format_input = QComboBox()
        self.format_input.addItems(['mkv', 'avi'])
        record_form.addRow("视频格式:", self.format_input)
        
        # 视频编码
        self.codec_input = QComboBox()
        self.codec_input.addItems(['h264', 'h265', 'vp9', 'av1'])
        record_form.addRow("视频编码:", self.codec_input)
        
        # 视频编码说明
        codec_note = QLabel("注：h264兼容性最好，h265文件更小，vp9和av1为开源编码")
        codec_note.setStyleSheet("color: #666; font-size: 9pt;")
        codec_note.setMinimumWidth(400)  # 设置足够的最小宽度
        codec_note.setWordWrap(False)    # 禁用自动换行
        record_form.addRow("", codec_note)
        
        # 分辨率
        self.resolution_input = QComboBox()
        self.resolution_input.addItems(['window', '1920x1080', '1280x720', '854x480', '640x360'])
        record_form.addRow("输出分辨率:", self.resolution_input)
        
        # 在分辨率选择下方添加说明
        resolution_note = QLabel("注：window表示与捕获分辨率相同，数字表示输出视频的分辨率")
        resolution_note.setStyleSheet("color: #666; font-size: 9pt;")
        resolution_note.setMinimumWidth(400)  # 设置足够的最小宽度
        resolution_note.setWordWrap(False)    # 禁用自动换行
        record_form.addRow("", resolution_note)
        
        # 显示器选择
        self.monitor_input = QComboBox()
        self.monitor_input.addItems(self.get_monitors_info())
        record_form.addRow("录制显示器:", self.monitor_input)
        
        # 音频设备
        self.audio_input = QComboBox()
        self.audio_input.addItems(self.get_audio_devices())
        record_form.addRow("音频设备:", self.audio_input)
        
        # 帧率选择
        self.framerate_input = QComboBox()
        self.framerate_input.addItems(['5', '10', '15', '20', '25', '30'])
        record_form.addRow("帧率:", self.framerate_input)
        
        # 录制质量
        self.quality_input = QComboBox()
        self.quality_input.addItems(['高', '中', '低'])
        record_form.addRow("录制质量:", self.quality_input)
        
        record_group.setLayout(record_form)
        basic_layout.addWidget(record_group)
        
        basic_tab.setLayout(basic_layout)
        
        # === 高级设置选项卡 ===
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout()
        
        # 添加循环任务选项组
        recurring_group = QGroupBox("循环任务设置")
        recurring_layout = QVBoxLayout()
        recurring_layout.setContentsMargins(10, 15, 10, 10)
        recurring_layout.setSpacing(10)
        
        # 启用循环任务选项
        self.enable_recurring_input = QCheckBox("启用循环任务")
        self.enable_recurring_input.setFixedHeight(24)
        recurring_layout.addWidget(self.enable_recurring_input)
        
        # 循环日期选项
        recurring_days_layout = QGridLayout()
        recurring_days_layout.setColumnStretch(0, 1)
        recurring_days_layout.setColumnStretch(1, 1)
        recurring_days_layout.setColumnStretch(2, 1)
        recurring_days_layout.setColumnStretch(3, 1)
        
        self.everyday_check = QCheckBox("每天")
        self.everyday_check.setFixedHeight(24)
        recurring_days_layout.addWidget(self.everyday_check, 0, 0)
        
        self.monday_check = QCheckBox("周一")
        self.monday_check.setFixedHeight(24)
        recurring_days_layout.addWidget(self.monday_check, 1, 0)
        
        self.tuesday_check = QCheckBox("周二")
        self.tuesday_check.setFixedHeight(24)
        recurring_days_layout.addWidget(self.tuesday_check, 1, 1)
        
        self.wednesday_check = QCheckBox("周三")
        self.wednesday_check.setFixedHeight(24)
        recurring_days_layout.addWidget(self.wednesday_check, 1, 2)
        
        self.thursday_check = QCheckBox("周四")
        self.thursday_check.setFixedHeight(24)
        recurring_days_layout.addWidget(self.thursday_check, 1, 3)
        
        self.friday_check = QCheckBox("周五")
        self.friday_check.setFixedHeight(24)
        recurring_days_layout.addWidget(self.friday_check, 2, 0)
        
        self.saturday_check = QCheckBox("周六")
        self.saturday_check.setFixedHeight(24)
        recurring_days_layout.addWidget(self.saturday_check, 2, 1)
        
        self.sunday_check = QCheckBox("周日")
        self.sunday_check.setFixedHeight(24)
        recurring_days_layout.addWidget(self.sunday_check, 2, 2)
        
        # 连接每天选项与其他日期选项的互斥关系
        self.everyday_check.stateChanged.connect(self.on_everyday_changed)
        self.monday_check.stateChanged.connect(self.on_specific_day_changed)
        self.tuesday_check.stateChanged.connect(self.on_specific_day_changed)
        self.wednesday_check.stateChanged.connect(self.on_specific_day_changed)
        self.thursday_check.stateChanged.connect(self.on_specific_day_changed)
        self.friday_check.stateChanged.connect(self.on_specific_day_changed)
        self.saturday_check.stateChanged.connect(self.on_specific_day_changed)
        self.sunday_check.stateChanged.connect(self.on_specific_day_changed)
        
        recurring_days_note = QLabel("注：录制结束后将自动设置下一个周期的开始时间并开始倒计时")
        recurring_days_note.setWordWrap(True)
        recurring_days_note.setStyleSheet("color: #666; font-size: 9pt;")
        
        recurring_layout.addLayout(recurring_days_layout)
        recurring_layout.addWidget(recurring_days_note)
        recurring_group.setLayout(recurring_layout)
        advanced_layout.addWidget(recurring_group)
        
        # 自动化选项组
        auto_group = QGroupBox("自动化选项")
        auto_grid = QGridLayout()  # 使用网格布局来更好地组织控件
        auto_grid.setContentsMargins(10, 15, 10, 10)
        auto_grid.setHorizontalSpacing(15)
        auto_grid.setVerticalSpacing(10)
        
        # 按照功能逻辑重新分组
        # 第一列：基本选项
        col1_label = QLabel("基本选项")
        col1_label.setStyleSheet("font-weight: bold; color: #4a86e8;")
        auto_grid.addWidget(col1_label, 0, 0)
        
        # 静默模式
        self.silent_input = QCheckBox("单纯录屏(不弹窗)")
        self.silent_input.setFixedHeight(24)
        auto_grid.addWidget(self.silent_input, 1, 0)
        
        # 第二列：播放控制
        col2_label = QLabel("播放控制")
        col2_label.setStyleSheet("font-weight: bold; color: #4a86e8;")
        auto_grid.addWidget(col2_label, 0, 1)
        
        # 全屏选项
        self.fullscreen_input = QCheckBox("自动全屏(H键)")
        self.fullscreen_input.setFixedHeight(24)
        auto_grid.addWidget(self.fullscreen_input, 1, 1)
        
        # 取消静音选项
        self.unmute_input = QCheckBox("取消静音(P键)")
        self.unmute_input.setFixedHeight(24)
        auto_grid.addWidget(self.unmute_input, 2, 1)
        
        # 浏览器全屏选项(F11)
        self.browser_fullscreen_input = QCheckBox("浏览器全屏(F11键)")
        self.browser_fullscreen_input.setFixedHeight(24)
        auto_grid.addWidget(self.browser_fullscreen_input, 3, 1)
        
        # B站全屏(F键)
        self.bilibili_fullscreen_input = QCheckBox("B站全屏(F键)")
        self.bilibili_fullscreen_input.setFixedHeight(24)
        auto_grid.addWidget(self.bilibili_fullscreen_input, 4, 1)
        
        # 第三列：自定义按键
        col3_label = QLabel("自定义按键")
        col3_label.setStyleSheet("font-weight: bold; color: #4a86e8;")
        auto_grid.addWidget(col3_label, 0, 2)
        
        # 自定义按键1
        self.custom_key1_check = QCheckBox("自定义按键1:")
        self.custom_key1_check.setFixedHeight(24)
        auto_grid.addWidget(self.custom_key1_check, 1, 2)
        
        self.custom_key1_input = QLineEdit()
        self.custom_key1_input.setFixedWidth(80)
        self.custom_key1_input.setMaxLength(1)  # 限制为单个字符
        self.custom_key1_input.setPlaceholderText("NULL")
        # 使用正则表达式验证器，只允许字母、数字和半角符号
        self.custom_key1_input.textChanged.connect(lambda: self.validate_custom_key(self.custom_key1_input))
        auto_grid.addWidget(self.custom_key1_input, 1, 3)
        
        # 自定义按键2
        self.custom_key2_check = QCheckBox("自定义按键2:")
        self.custom_key2_check.setFixedHeight(24)
        auto_grid.addWidget(self.custom_key2_check, 2, 2)
        
        self.custom_key2_input = QLineEdit()
        self.custom_key2_input.setFixedWidth(80)
        self.custom_key2_input.setMaxLength(1)  # 限制为单个字符
        self.custom_key2_input.setPlaceholderText("NULL")
        # 使用正则表达式验证器，只允许字母、数字和半角符号
        self.custom_key2_input.textChanged.connect(lambda: self.validate_custom_key(self.custom_key2_input))
        auto_grid.addWidget(self.custom_key2_input, 2, 3)
        
        # 设置列的拉伸因子，使列1和列2更宽
        auto_grid.setColumnStretch(0, 1)
        auto_grid.setColumnStretch(1, 2)
        auto_grid.setColumnStretch(2, 1)
        auto_grid.setColumnStretch(3, 1)
        
        auto_group.setLayout(auto_grid)
        advanced_layout.addWidget(auto_group)
        
        # 说明信息
        info_group = QGroupBox("使用说明")
        info_layout = QVBoxLayout()
        
        info_text = QLabel(
            "1. 设置直播地址和录制参数\n"
            "2. 选择开始时间和录制时长\n"
            "3. 点击「开始任务」，工具会在指定时间自动开始录制\n"
            "4. 录制过程中会自动模拟点击防止直播暂停\n"
            "5. 录制完成后，视频会保存到指定路径\n"
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        info_group.setLayout(info_layout)
        advanced_layout.addWidget(info_group)
        advanced_layout.addStretch(1)
        
        advanced_tab.setLayout(advanced_layout)
        
        # 添加选项卡
        tab_widget.addTab(basic_tab, "基本设置")
        tab_widget.addTab(advanced_tab, "高级设置")
        
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(tab_widget)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton('开始任务')
        self.start_btn.setIcon(self.create_svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="white" d="M8 5v14l11-7z"/></svg>'
        ))
        self.start_btn.setIconSize(QSize(18, 18))
        
        self.stop_btn = QPushButton('停止任务')
        self.stop_btn.setIcon(self.create_svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="white" d="M6 6h12v12H6z"/></svg>'
        ))
        self.stop_btn.setIconSize(QSize(18, 18))
        
        self.start_btn.setMinimumHeight(40)
        self.stop_btn.setMinimumHeight(40)
        
        # 按钮样式与悬停效果
        button_style = """
            QPushButton {
                background-color: %s;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: %s;
            }
            QPushButton:pressed {
                background-color: %s;
            }
        """
        
        # 开始任务按钮 - 蓝色
        self.start_btn.setStyleSheet(button_style % ('#4a86e8', '#3a76d8', '#2a66c8'))
        
        # 停止任务按钮 - 红色，禁用时为灰色
        self.stop_btn.setStyleSheet('''
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover:!disabled {
                background-color: #d44637;
            }
            QPushButton:pressed:!disabled {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        ''')
        
        self.start_btn.clicked.connect(self.on_start_record)
        self.stop_btn.clicked.connect(self.on_stop_record)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
        self.stop_btn.setDisabled(True)  # 初始为禁用

    def choose_save_path(self):
        path = QFileDialog.getExistingDirectory(self, '选择保存路径', './')
        if path:
            self.save_path_input.setText(path)

    def get_audio_devices(self):
        devices = ['无音频']
        try:
            ffmpeg_path = get_ffmpeg_path()
            result = subprocess.run(
                [ffmpeg_path, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf-8'
            )
            for line in result.stderr.splitlines():
                if 'Alternative name' in line:
                    continue
                m = re.search(r'"(.+?)"', line)
                if m and 'audio devices' not in line and 'DirectShow audio devices' not in line:
                    devices.append(m.group(1).strip())
        except Exception as e:
            print("获取音频设备失败：", e)
        return devices

    def get_monitors_info(self):
        monitors = []
        try:
            # 获取所有显示器并按照从左到右的顺序排序
            all_monitors = get_monitors()
            sorted_monitors = sorted(all_monitors, key=lambda m: m.x)
            for i, m in enumerate(sorted_monitors):
                monitors.append(f"显示器 {i+1} ({m.width}x{m.height})")
        except Exception:
            # 如果无法获取监视器信息，提供默认值
            monitors = ["主显示器", "扩展显示器"]
        return monitors

    def validate_custom_key(self, line_edit):
        """验证自定义按键输入，只允许字母、数字和半角符号"""
        text = line_edit.text()
        # 只保留字母、数字和半角符号
        valid_chars = "".join(ch for ch in text if ch.isalnum() or ch in '`~!@#$%^&*()-_=+[]{}\\|;:\'\",.<>/?')
        # 如果输入不合法，替换为合法内容
        if text != valid_chars:
            line_edit.setText(valid_chars)
            
    def load_config_to_ui(self):
        self.url_input.setText(self.config.get('douyin_url', ''))
        self.start_time_input.setDateTime(QDateTime.fromString(self.config.get('start_time', ''), 'yyyy-MM-dd HH:mm:ss'))
        self.duration_input.setValue(self.config.get('duration_minutes', 60))
        self.save_path_input.setText(self.config.get('save_path', './videos'))
        self.format_input.setCurrentText(self.config.get('video_format', 'mkv'))
        self.codec_input.setCurrentText(self.config.get('video_codec', 'h264'))
        self.resolution_input.setCurrentText(self.config.get('resolution', 'window'))
        
        # 显示器选择
        monitor_index = self.config.get('monitor_index', 0)
        if monitor_index < self.monitor_input.count():
            self.monitor_input.setCurrentIndex(monitor_index)
            
        # 音频设备
        audio_device = self.config.get('audio_device', '无音频')
        idx = self.audio_input.findText(audio_device)
        if idx != -1:
            self.audio_input.setCurrentIndex(idx)
        else:
            self.audio_input.setCurrentIndex(0)
            
        # 新增选项
        self.framerate_input.setCurrentText(self.config.get('framerate', '25'))
        self.quality_input.setCurrentText(self.config.get('record_quality', '中'))
            
        # 自动化选项
        self.silent_input.setChecked(self.config.get('silent_mode', False))
        self.fullscreen_input.setChecked(self.config.get('enable_fullscreen', True))
        self.unmute_input.setChecked(self.config.get('enable_unmute', True))
        self.browser_fullscreen_input.setChecked(self.config.get('enable_browser_fullscreen', False))
        self.bilibili_fullscreen_input.setChecked(self.config.get('enable_bilibili_fullscreen', False))
        
        # 自定义按键选项
        self.custom_key1_check.setChecked(self.config.get('custom_key1_enabled', False))
        self.custom_key1_input.setText(self.config.get('custom_key1', ''))
        self.custom_key2_check.setChecked(self.config.get('custom_key2_enabled', False))
        self.custom_key2_input.setText(self.config.get('custom_key2', ''))
        
        # 循环任务设置 - 先加载各个星期的设置
        recurring_days = self.config.get('recurring_days', {})
        self.monday_check.setChecked(recurring_days.get('monday', False))
        self.tuesday_check.setChecked(recurring_days.get('tuesday', False))
        self.wednesday_check.setChecked(recurring_days.get('wednesday', False))
        self.thursday_check.setChecked(recurring_days.get('thursday', False))
        self.friday_check.setChecked(recurring_days.get('friday', False))
        self.saturday_check.setChecked(recurring_days.get('saturday', False))
        self.sunday_check.setChecked(recurring_days.get('sunday', False))
        
        # 然后设置"每天"选项，这样会自动处理所有日期的勾选状态
        self.enable_recurring_input.setChecked(self.config.get('enable_recurring', False))
        everyday_checked = recurring_days.get('everyday', False)
        self.everyday_check.setChecked(everyday_checked)

    def save_ui_to_config(self):
        # 先获取静默模式的设置
        silent_mode = self.silent_input.isChecked()
        
        # 获取URL
        url = self.url_input.text().strip()
        
        # 验证和处理URL，如果是静默模式则不验证
        processed_url, is_valid, error_message = validate_live_url(url, silent_mode=silent_mode)
        
        # 更新输入框为处理后的URL
        if processed_url != url:
            self.url_input.setText(processed_url)
            
        # 保存到配置
        self.config['douyin_url'] = processed_url
        self.config['url_is_valid'] = is_valid
        self.config['url_error_message'] = error_message
        
        # 继续保存其他配置项
        self.config['start_time'] = self.start_time_input.dateTime().toString('yyyy-MM-dd HH:mm:ss')
        self.config['duration_minutes'] = self.duration_input.value()
        self.config['save_path'] = self.save_path_input.text()
        self.config['video_format'] = self.format_input.currentText()
        self.config['video_codec'] = self.codec_input.currentText()
        self.config['resolution'] = self.resolution_input.currentText()
        self.config['monitor_index'] = self.monitor_input.currentIndex()
        self.config['audio_device'] = self.audio_input.currentText()
        self.config['silent_mode'] = silent_mode
        self.config['enable_fullscreen'] = self.fullscreen_input.isChecked()
        self.config['enable_unmute'] = self.unmute_input.isChecked()
        self.config['enable_browser_fullscreen'] = self.browser_fullscreen_input.isChecked()
        self.config['enable_bilibili_fullscreen'] = self.bilibili_fullscreen_input.isChecked()
        self.config['framerate'] = self.framerate_input.currentText()
        self.config['record_quality'] = self.quality_input.currentText()
        
        self.config['custom_key1_enabled'] = self.custom_key1_check.isChecked()
        self.config['custom_key1'] = self.custom_key1_input.text()
        self.config['custom_key2_enabled'] = self.custom_key2_check.isChecked()
        self.config['custom_key2'] = self.custom_key2_input.text()
        
        # 保存循环任务设置
        self.config['enable_recurring'] = self.enable_recurring_input.isChecked()
        self.config['recurring_days'] = {
            'monday': self.monday_check.isChecked(),
            'tuesday': self.tuesday_check.isChecked(),
            'wednesday': self.wednesday_check.isChecked(),
            'thursday': self.thursday_check.isChecked(),
            'friday': self.friday_check.isChecked(),
            'saturday': self.saturday_check.isChecked(),
            'sunday': self.sunday_check.isChecked(),
            'everyday': self.everyday_check.isChecked()
        }
        
        # 保存配置
        save_config(self.config)

    def on_start_record(self):
        self.save_ui_to_config()
        
        # 检查URL是否有效，如果不是静默模式
        if not self.silent_input.isChecked() and not self.config.get('url_is_valid', True):
            # 显示错误消息
            error_message = self.config.get('url_error_message', "地址非法，改为纯录屏模式")
            QMessageBox.warning(self, '提示', error_message)
            
            # 强制设置为静默模式（纯录屏）
            self.config['silent_mode'] = True
            self.silent_input.setChecked(True)
            
            # 重新保存配置
            self.save_ui_to_config()
        
        # 计数器递增
        self.click_count += 1
        
        # 检查是否是快速双击
        if self.click_count == 1:
            self.click_timer.start(500)  # 500毫秒内再次点击视为双击
        elif self.click_count >= 2:
            # 双击立即开始录制
            self.start_immediate_recording()
            return
        
        # 检查是否已经在倒计时状态
        if self.countdown_timer.isActive():
            # 倒计时状态下，点击按钮直接开始任务
            self.start_immediate_recording()
            return
        
        # 校验时间
        start_time_str = self.start_time_input.dateTime().toString('yyyy-MM-dd HH:mm:ss')
        self.start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        
        if self.start_time <= datetime.now():
            QMessageBox.warning(self, '警告', '开始时间必须晚于当前时间！')
            return
        
        # 重新调度任务
        if hasattr(self.scheduler, 'scheduler'):
            self.scheduler.config = self.config  # 更新调度器配置
            self.scheduler.schedule_recording()
        
        # 开始倒计时
        self.start_countdown()

    def reset_click_counter(self):
        """重置点击计数器"""
        self.click_count = 0
        
    def start_immediate_recording(self, show_popup=True):
        if self.is_recording:
            return
            
        # 保存当前UI设置到配置
        self.save_ui_to_config()
        
        # 检查URL有效性，如果不是静默模式且URL无效，则切换到纯录屏模式
        if not self.config.get('silent_mode', False) and not self.config.get('url_is_valid', True):
            # 显示错误消息
            error_message = self.config.get('url_error_message', "地址非法，改为纯录屏模式")
            QMessageBox.warning(self, '提示', error_message)
            
            # 强制设置为静默模式（纯录屏）
            self.config['silent_mode'] = True
            self.silent_input.setChecked(True)
            
            # 重新保存配置
            self.save_ui_to_config()
            
        self.is_recording = True
        self.stop_countdown()
        self.disable_all_settings(True)
        self.stop_btn.setDisabled(False)  # 启用停止按钮
        # 配置中
        self.start_btn.setText("配置中")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:pressed {
                background-color: #d35400;
            }
        """)
        QApplication.processEvents()
        
        # 只有在URL有效且不是静默模式的情况下才打开浏览器
        if not self.config.get('silent_mode', False) and self.config.get('url_is_valid', True):
            # 打开浏览器并自动化操作
            browser_controller_instance.silent_mode = self.config.get('silent_mode', False)
            browser_controller_instance.open_live_page(
                self.config['douyin_url'],
                monitor_index=self.config.get('monitor_index', 0),
                fullscreen=self.config.get('enable_fullscreen', True),
                unmute=self.config.get('enable_unmute', True),
                browser_fullscreen=self.config.get('enable_browser_fullscreen', False),
                bilibili_fullscreen=self.config.get('enable_bilibili_fullscreen', False),
                custom_key1_enabled=self.config.get('custom_key1_enabled', False),
                custom_key1=self.config.get('custom_key1', ''),
                custom_key2_enabled=self.config.get('custom_key2_enabled', False),
                custom_key2=self.config.get('custom_key2', '')
            )
            # 启动定时点击
            self.clicker = Clicker(browser_controller_instance.driver, interval=60)
            self.clicker.start()
            
        # 配置完成，切换为录制中
        now = datetime.now()
        self.config['start_time'] = now.strftime('%Y-%m-%d %H:%M:%S')
        duration_minutes = self.config.get('duration_minutes', 60)
        self.record_end_time = now + timedelta(minutes=duration_minutes)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d44637;
            }
            QPushButton:pressed {
                background-color: #c0392b;
            }
        """)
        self.start_btn.setDisabled(False)  # 录制中允许点击
        self.start_btn.clicked.disconnect()
        self.start_btn.clicked.connect(self.extend_recording_time)
        # 启动录制倒计时刷新
        self.record_timer = QTimer(self)
        self.record_timer.timeout.connect(self.update_recording_countdown)
        self.record_timer.start(1000)
        self.update_recording_countdown()  # 立即刷新一次
        QApplication.processEvents()
        # 启动录制
        from recorder.recorder import recorder_instance
        recorder_instance.start_recording(self.config)
        if hasattr(self.scheduler, 'scheduler'):
            try:
                self.scheduler.scheduler.remove_job('stop_record')
            except Exception:
                pass
            self.scheduler.scheduler.add_job(
                self.scheduler.stop_all, 
                'date', 
                run_date=self.record_end_time, 
                id='stop_record'
            )
        # 不再弹窗提示录制已开始

    def extend_recording_time(self):
        # 录制中点击按钮，延长1分钟
        if not self.is_recording:
            return
        self.record_end_time += timedelta(minutes=1)
        # 更新APScheduler的stop_record任务
        if hasattr(self.scheduler, 'scheduler'):
            try:
                self.scheduler.scheduler.remove_job('stop_record')
            except Exception:
                pass
            self.scheduler.scheduler.add_job(
                self.scheduler.stop_all,
                'date',
                run_date=self.record_end_time,
                id='stop_record'
            )
        self.update_recording_countdown()

    def update_recording_countdown(self):
        if not hasattr(self, 'record_end_time') or not self.is_recording:
            return
        now = datetime.now()
        remain = self.record_end_time - now
        if remain.total_seconds() <= 0:
            self.start_btn.setText("录制中（0分0秒）")
            if hasattr(self, 'record_timer'):
                self.record_timer.stop()
            return
        minutes, seconds = divmod(int(remain.total_seconds()), 60)
        self.start_btn.setText(f"录制中（{minutes}分{seconds}秒）")

    def start_countdown(self):
        """启动倒计时"""
        # 确保start_time变量被正确设置，用于倒计时检查
        start_time_str = self.start_time_input.dateTime().toString('yyyy-MM-dd HH:mm:ss')
        self.start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        
        self.countdown_timer.start(1000)  # 每秒更新一次
        self.update_countdown()  # 立即更新一次
        self.disable_all_settings(True)
        self.stop_btn.setDisabled(False)  # 启用停止按钮
        
    def stop_countdown(self):
        """停止倒计时"""
        self.countdown_timer.stop()
        self.start_btn.setText(self.original_btn_text)
        self.disable_all_settings(False)
        self.stop_btn.setDisabled(True)  # 禁用停止按钮
        
    def disable_all_settings(self, disabled):
        # 基本设置
        self.url_input.setDisabled(disabled)
        self.start_time_input.setDisabled(disabled)
        self.duration_input.setDisabled(disabled)
        self.save_path_input.setDisabled(disabled)
        self.browse_btn.setDisabled(disabled)
        self.format_input.setDisabled(disabled)
        self.resolution_input.setDisabled(disabled)
        self.monitor_input.setDisabled(disabled)
        self.audio_input.setDisabled(disabled)
        self.codec_input.setDisabled(disabled)
        self.framerate_input.setDisabled(disabled)
        self.quality_input.setDisabled(disabled)
        
        # 自动化选项
        self.silent_input.setDisabled(disabled)
        self.fullscreen_input.setDisabled(disabled)
        self.unmute_input.setDisabled(disabled)
        self.browser_fullscreen_input.setDisabled(disabled)
        self.bilibili_fullscreen_input.setDisabled(disabled)
        self.custom_key1_input.setDisabled(disabled)
        self.custom_key1_check.setDisabled(disabled)
        self.custom_key2_input.setDisabled(disabled)
        self.custom_key2_check.setDisabled(disabled)
        
        # 循环任务设置
        self.enable_recurring_input.setDisabled(disabled)
        self.everyday_check.setDisabled(disabled)
        self.monday_check.setDisabled(disabled)
        self.tuesday_check.setDisabled(disabled)
        self.wednesday_check.setDisabled(disabled)
        self.thursday_check.setDisabled(disabled)
        self.friday_check.setDisabled(disabled)
        self.saturday_check.setDisabled(disabled)
        self.sunday_check.setDisabled(disabled)
        
        # 更新UI
        QApplication.processEvents()
        
    def update_countdown(self):
        """更新倒计时显示"""
        logger = logging.getLogger(__name__)
        
        now = datetime.now()
        if self.start_time:
            # 计算剩余时间
            time_diff = self.start_time - now
            
            if time_diff.total_seconds() <= 0:
                # 时间到，停止倒计时并立即开始录制
                logger.info(f"倒计时结束，开始时间: {self.start_time}，当前时间: {now}")
                logger.info("停止倒计时并立即开始录制")
                self.stop_countdown()
                self.start_immediate_recording()
                return
                
            # 格式化显示
            days = time_diff.days
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                countdown_text = f"开始任务 ({days}天{hours}时{minutes}分)"
            elif hours > 0:
                countdown_text = f"开始任务 ({hours}时{minutes}分{seconds}秒)"
            else:
                countdown_text = f"开始任务 ({minutes}分{seconds}秒)"
                
            self.start_btn.setText(countdown_text)

    def on_stop_record(self, show_popup=True):
        """
        停止录制的方法，负责清理资源并重置UI状态
        
        参数:
            show_popup: 是否显示提示弹窗。手动停止时为True，自动(计划)停止时为False
        """
        if self.countdown_timer.isActive():
            self.stop_countdown()
            if hasattr(self.scheduler, 'scheduler'):
                for job_id in ['start_record', 'stop_record']:
                    try:
                        self.scheduler.scheduler.remove_job(job_id)
                    except Exception:
                        pass
            self.show_status('任务已取消', show_popup=show_popup)
            return
        if hasattr(self, 'clicker') and self.clicker:
            self.clicker.stop()
            self.clicker = None
        from browser.browser_controller import browser_controller_instance
        browser_controller_instance.close()
        from recorder.recorder import recorder_instance
        recorder_instance.stop_recording()
        self.disable_all_settings(False)
        self.start_btn.setText(self.original_btn_text)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:pressed {
                background-color: #2a66c8;
            }
        """)
        self.start_btn.setDisabled(False)
        self.stop_btn.setDisabled(True)  # 禁用停止按钮
        self.is_recording = False
        if hasattr(self, 'record_timer'):
            self.record_timer.stop()
        # 修复：恢复"开始任务"按钮的信号绑定
        try:
            self.start_btn.clicked.disconnect()
        except Exception:
            pass
        self.start_btn.clicked.connect(self.on_start_record)
        
        # 完全删除弹窗显示逻辑，无论是循环任务还是普通任务
        if not show_popup:
            return

    def show_status(self, msg, show_popup=True):
        # 如果不显示弹窗，则只记录日志
        if not show_popup:
            logger = logging.getLogger(__name__)
            logger.info(f"状态信息(不显示): {msg}")
            return
            
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('状态')
        msg_box.setText(msg)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStyleSheet("""
            QMessageBox {
                font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif;
                font-size: 11pt;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
        """)
        
        # 设置窗口大小适中
        msg_box.setFixedWidth(300)
        
        # 添加计时器自动关闭（2秒）
        QTimer.singleShot(2000, msg_box.close)
        
        msg_box.exec_()

    def create_svg_icon(self, svg_data):
        pixmap = QPixmap()
        pixmap.loadFromData(svg_data.encode('utf-8'), 'SVG')
        return QIcon(pixmap)

    def on_schedule_start_record(self):
        self.start_immediate_recording(show_popup=False)

    def on_schedule_stop_record(self):
        # 调度器触发的停止录制，不显示弹窗提示
        logger = logging.getLogger(__name__)
        logger.info("调度器触发停止录制")
        self.on_stop_record(show_popup=False)
        
        # 当停止录制后，如果启用了循环任务，确保手动调用调度器的循环方法
        if self.config.get('enable_recurring', False) and hasattr(self.scheduler, 'schedule_next_recurring'):
            logger.info("启用了循环任务，手动调用下一个循环设置")
            self.scheduler.schedule_next_recurring()

    # 处理"每天"选项与特定日期选项的关系
    def on_everyday_changed(self, state):
        if state == Qt.Checked:
            # 如果勾选"每天"，则自动勾选所有特定日期
            self.monday_check.setChecked(True)
            self.tuesday_check.setChecked(True)
            self.wednesday_check.setChecked(True)
            self.thursday_check.setChecked(True)
            self.friday_check.setChecked(True)
            self.saturday_check.setChecked(True)
            self.sunday_check.setChecked(True)
        # 当取消勾选"每天"时，不再自动取消所有日期的勾选，保持当前状态

    def on_specific_day_changed(self, state):
        # 如果取消勾选了某一天，只需要取消"每天"的勾选
        if state == Qt.Unchecked and self.everyday_check.isChecked():
            self.everyday_check.setChecked(False)
            # 取消勾选某一天时，不影响其他天的选择状态
            return
            
        # 检查是否选中了所有天
        all_days_checked = (
            self.monday_check.isChecked() and
            self.tuesday_check.isChecked() and
            self.wednesday_check.isChecked() and
            self.thursday_check.isChecked() and
            self.friday_check.isChecked() and
            self.saturday_check.isChecked() and
            self.sunday_check.isChecked()
        )
        
        # 更新"每天"复选框的状态
        if all_days_checked:
            # 如果所有天都选中，则自动勾选"每天"
            self.everyday_check.setChecked(True)

    # 添加closeEvent方法，在窗口关闭前保存配置
    def closeEvent(self, event):
        """
        在窗口关闭前保存当前配置，确保用户设置不会丢失
        """
        logger = logging.getLogger(__name__)
        logger.info("应用程序关闭，保存当前配置")
        
        # 保存当前UI设置到配置文件
        self.save_ui_to_config()
        
        # 继续正常的关闭事件
        super().closeEvent(event)

def start_gui(config, scheduler):
    app = QApplication(sys.argv)
    window = MainWindow(config, scheduler)
    window.show()
    
    # 确保应用程序在退出前保存配置（额外保险措施）
    app.aboutToQuit.connect(lambda: shutdown_cleanup(window, config))
    
    sys.exit(app.exec_()) 

def shutdown_cleanup(window, config):
    """程序退出前的清理工作"""
    logger = logging.getLogger(__name__)
    logger.info("程序即将退出，执行最终保存和清理")
    
    # 确保保存最新配置
    window.save_ui_to_config()
    
    # 这里可以添加其他清理工作，如关闭日志等 