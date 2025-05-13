from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from screeninfo import get_monitors
import time
import os

def get_monitor_geometry(monitor_index=0):
    try:
        monitors = get_monitors()
        # 从左往右排序显示器（按x坐标排序）
        monitors = sorted(monitors, key=lambda m: m.x)
        if 0 <= monitor_index < len(monitors):
            m = monitors[monitor_index]
            return m.x, m.y, m.width, m.height
    except Exception:
        pass
    
    # 默认值，如果获取失败
    if monitor_index == 0:  # 主显示器
        return 0, 0, 1920, 1080
    else:  # 假设第二显示器在右侧
        return 1920, 0, 1920, 1080

class BrowserController:
    def __init__(self, silent_mode=False):
        self.driver = None
        self.silent_mode = silent_mode
        self.monitor_index = 0  # 默认使用主显示器
        
        # 改进用户配置文件路径，使用项目内的文件夹以便于携带
        self.user_data_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chrome_profile'))
        os.makedirs(self.user_data_dir, exist_ok=True)

    def open_live_page(self, url, monitor_index=None, fullscreen=True, unmute=True, browser_fullscreen=False, bilibili_fullscreen=False, custom_key1_enabled=False, custom_key1="", custom_key2_enabled=False, custom_key2=""):
        if monitor_index is not None:
            self.monitor_index = monitor_index
            
        options = Options()
        if self.silent_mode:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
        
        # 使用本地目录保存用户配置，确保登录信息不丢失
        options.add_argument(f'--user-data-dir={self.user_data_dir}')
        options.add_argument('--profile-directory=Default')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-extensions')
        # 禁用自动化标识，减少被网站检测的可能
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 使用Service对象创建driver
        self.driver = webdriver.Chrome(options=options)
        
        # 如果不是静默模式，将浏览器窗口移动到指定显示器
        if not self.silent_mode:
            # 获取指定显示器的位置和尺寸
            x, y, width, height = get_monitor_geometry(self.monitor_index)
            
            # 先让浏览器窗口加载到指定位置
            self.driver.set_window_position(x, y)
            self.driver.set_window_size(width, height)
            
            # 然后再加载URL，确保在正确的显示器上打开
            self.driver.get(url)
            time.sleep(5)  # 延长等待时间，确保网页完全加载
            
            # 再次确认窗口位置和大小，因为页面加载可能会改变窗口
            self.driver.set_window_position(x, y)
            self.driver.set_window_size(width, height)
            # 最大化窗口（在指定显示器内）
            self.driver.maximize_window()
            
            # 根据用户设置执行按键操作
            time.sleep(2)  # 额外等待，确保页面元素完全加载
            
            # 按H键实现全屏显示（如果启用）
            if fullscreen:
                self.press_key('h')
                
            # 按P键取消静音（如果启用）
            if unmute:
                time.sleep(1)  # 先等待一秒，确保全屏切换完成
                self.press_key('p')
                
            # 按F11键实现浏览器全屏（如果启用）
            if browser_fullscreen:
                time.sleep(1)  # 等待前面的操作完成
                self.press_key(Keys.F11)
                
            # 按F键实现B站全屏（如果启用）
            if bilibili_fullscreen:
                time.sleep(1)  # 等待前面的操作完成
                self.press_key('f')
                
            # 按自定义按键1（如果启用且有设置）
            if custom_key1_enabled and custom_key1:
                time.sleep(1)  # 等待前面的操作完成
                self.press_key(custom_key1)
                
            # 按自定义按键2（如果启用且有设置）
            if custom_key2_enabled and custom_key2:
                time.sleep(1)  # 等待前面的操作完成
                self.press_key(custom_key2)
        else:
            # 静默模式
            self.driver.get(url)
            
        time.sleep(3)  # 等待操作完成

    def press_key(self, key):
        """发送单个按键"""
        if not self.driver:
            return False
        try:
            actions = ActionChains(self.driver)
            actions.send_keys(key).perform()
            time.sleep(0.5)  # 短暂等待按键生效
            return True
        except Exception:
            return False

    def close(self):
        if self.driver:
            try:
                # 退出全屏模式（再次按H键）
                self.press_key('h')
                time.sleep(1)
            except:
                pass
            self.driver.quit()
            self.driver = None

    def get_window_position(self):
        if self.driver:
            pos = self.driver.get_window_position()
            size = self.driver.get_window_size()
            return {"x": pos['x'], "y": pos['y'], "width": size['width'], "height": size['height']}
        return None

browser_controller_instance = BrowserController() 