@echo off
chcp 65001
REM ====== 打包Python程序为单文件可执行 ======
REM 1. 清理旧的build和dist目录
rmdir /s /q build
rmdir /s /q dist

REM 2. 执行PyInstaller打包
pyinstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --icon=assets\icon.ico ^
  --add-data "assets;assets" ^
  --add-data "config;config" ^
  --add-data "chrome_profile;chrome_profile" ^
  --add-data "recorder;recorder" ^
  --add-data "browser;browser" ^
  --add-data "scheduler;scheduler" ^
  --add-data "utils;utils" ^
  --add-data "ffmpeg;ffmpeg" ^
  main.py

echo.
echo 打包完成！可执行文件在 dist 目录下。
pause 