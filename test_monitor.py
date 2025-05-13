#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from browser.browser_controller import browser_controller_instance, get_monitor_geometry
from screeninfo import get_monitors

def test_monitors():
    """测试获取显示器信息和排序"""
    print("===== 显示器测试 =====")
    
    # 获取所有显示器并按照从左到右的顺序排序
    try:
        all_monitors = get_monitors()
        print(f"检测到 {len(all_monitors)} 个显示器:")
        
        # 原始顺序
        print("原始顺序:")
        for i, m in enumerate(all_monitors):
            print(f"显示器 {i+1}: 位置({m.x},{m.y}) 分辨率({m.width}x{m.height})")
        
        # 排序后
        sorted_monitors = sorted(all_monitors, key=lambda m: m.x)
        print("\n从左到右排序:")
        for i, m in enumerate(sorted_monitors):
            print(f"显示器 {i+1}: 位置({m.x},{m.y}) 分辨率({m.width}x{m.height})")
            
        # 测试几何获取函数
        print("\n调用 get_monitor_geometry 函数:")
        for i in range(len(sorted_monitors)):
            x, y, width, height = get_monitor_geometry(i)
            print(f"显示器 {i+1}: 位置({x},{y}) 分辨率({width}x{height})")
            
    except Exception as e:
        print(f"获取显示器信息失败: {e}")
        return False
    
    return True

def test_browser(monitor_index=0, fullscreen=True, unmute=True):
    """测试在指定显示器上打开浏览器"""
    print(f"\n===== 浏览器测试（显示器 {monitor_index+1}） =====")
    print(f"全屏: {'启用' if fullscreen else '禁用'}")
    print(f"取消静音: {'启用' if unmute else '禁用'}")
    
    try:
        # 打开浏览器到指定显示器
        browser_controller_instance.silent_mode = False
        browser_controller_instance.open_live_page(
            "https://www.douyin.com",
            monitor_index=monitor_index,
            fullscreen=fullscreen,
            unmute=unmute
        )
        
        # 获取窗口位置
        pos = browser_controller_instance.get_window_position()
        if pos:
            print(f"浏览器窗口位置: x={pos['x']}, y={pos['y']}, 大小={pos['width']}x{pos['height']}")
        
        # 测试按键功能
        time.sleep(5)
        print("\n测试按键功能:")
        
        # 测试H键（全屏/取消全屏）
        print("- 按H键切换全屏状态...")
        browser_controller_instance.press_key('h')
        time.sleep(3)
        
        # 测试P键（静音/取消静音）
        print("- 按P键切换静音状态...")
        browser_controller_instance.press_key('p')
        time.sleep(3)
        
        # 等待关闭
        print("\n浏览器将在10秒后关闭...")
        time.sleep(10)
        browser_controller_instance.close()
        print("浏览器已关闭")
        
    except Exception as e:
        print(f"浏览器测试失败: {e}")
        return False
    
    return True

def test_keyboard_options():
    """测试各种键盘选项组合"""
    try:
        all_monitors = sorted(get_monitors(), key=lambda m: m.x)
        monitor_count = len(all_monitors)
        choice = input(f"\n请选择要测试的显示器 (1-{monitor_count}): ")
        monitor_index = int(choice) - 1
        
        if 0 <= monitor_index < monitor_count:
            # 测试模式选择
            print("\n选择要测试的模式:")
            print("1. 全部启用 (全屏+取消静音)")
            print("2. 仅全屏")
            print("3. 仅取消静音")
            print("4. 全部禁用")
            
            mode = input("请选择 (1-4): ")
            
            if mode == "1":
                test_browser(monitor_index, True, True)
            elif mode == "2":
                test_browser(monitor_index, True, False)
            elif mode == "3":
                test_browser(monitor_index, False, True)
            elif mode == "4":
                test_browser(monitor_index, False, False)
            else:
                print("无效的选择，使用默认模式")
                test_browser(monitor_index)
        else:
            print("无效的显示器选择")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    # 测试显示器
    if test_monitors():
        test_keyboard_options()
    print("\n测试完成") 