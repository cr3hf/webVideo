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
  --name webVideoRecord ^
  --icon=assets\icon.ico ^
  --add-data "assets;assets" ^
  --add-data "config;config" ^
  --add-data "recorder;recorder" ^
  --add-data "browser;browser" ^
  --add-data "scheduler;scheduler" ^
  --add-data "utils;utils" ^
  --add-data "ffmpeg;ffmpeg" ^
  --add-data "VERSION.md;." ^
  main.py

REM 3. 清理打包过程中产生的临时文件
rmdir /s /q build

echo.
echo 打包完成！可执行文件：dist\webVideoRecord.exe
pause 