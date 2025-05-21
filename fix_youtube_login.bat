@echo off
chcp 65001
echo 正在修复YouTube登录问题...

REM 备份原始文件
if exist browser\browser_controller.py.bak (
  echo 发现备份文件，跳过备份步骤
) else (
  echo 备份原始文件...
  copy browser\browser_controller.py browser\browser_controller.py.bak
)

REM 应用新文件
if exist browser\browser_controller_improved.py (
  echo 应用改进版浏览器控制器...
  copy /Y browser\browser_controller_improved.py browser\browser_controller.py
  echo 修复完成！
  
  REM 清理用户配置文件以确保新设置生效
  echo 是否要清除现有浏览器配置以确保修复生效？（y/n）
  set /p clearProfile=
  
  if /i "%clearProfile%"=="y" (
    echo 清理现有浏览器配置...
    if exist "%APPDATA%\WebVideoRecorder\chrome_profile" (
      rmdir /s /q "%APPDATA%\WebVideoRecorder\chrome_profile"
      echo 浏览器配置已清理，首次使用时需要重新登录。
    ) else (
      echo 未找到浏览器配置，无需清理。
    )
  ) else (
    echo 保留现有浏览器配置。
  )
) else (
  echo 错误：未找到改进版浏览器控制器文件，修复失败！
)

echo.
echo 重要提示：
echo 1. 请重新运行应用并访问需要登录的网站（如YouTube）
echo 2. 手动登录一次后，系统将保存登录状态
echo 3. 在后续使用中将无需重复登录
echo.

pause 