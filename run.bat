@echo off
chcp 65001 >nul
echo ========================================
echo    BLE RF Test Studio 启动中...
echo ========================================
echo.

REM 检查虚拟环境是否存在
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 未找到虚拟环境！
    echo 请先运行: python -m venv venv
    echo 然后运行: venv\Scripts\activate.bat
    echo 安装依赖: pip install -r requirements.txt
    pause
    exit /b 1
)

REM 使用 call 命令激活虚拟环境，确保在当前 shell 中执行
call venv\Scripts\activate.bat

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 未正确安装或配置！
    pause
    exit /b 1
)

echo [信息] 正在启动应用...
echo.
python src/main.py

REM 如果程序异常退出，显示错误信息
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出，错误代码: %errorlevel%
)

echo.
pause
