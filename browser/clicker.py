import time
from threading import Thread
from selenium.webdriver.common.action_chains import ActionChains

class Clicker:
    def __init__(self, driver, interval=60):
        self.driver = driver
        self.interval = interval  # 单位：秒
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.running:
            try:
                # 在页面中心点击
                actions = ActionChains(self.driver)
                actions.move_by_offset(10, 10).click().perform()
            except Exception:
                pass
            time.sleep(self.interval)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None 