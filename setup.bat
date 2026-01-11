@echo off
chcp 65001 >nul
echo ========================================
echo    BLE RF Test Studio 环境安装
echo ========================================
echo.

REM 检查 Python 是否已安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python！
    echo 请先安装 Python 3.9 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [信息] 检测到 Python 版本:
python --version
echo.

REM 检查虚拟环境是否已存在
if exist "venv\" (
    echo [警告] 虚拟环境已存在！
    set /p choice="是否删除并重新创建? (Y/N): "
    if /i "%choice%"=="Y" (
        echo [信息] 正在删除旧的虚拟环境...
        rmdir /s /q venv
    ) else (
        echo [信息] 保留现有虚拟环境，直接安装依赖...
        goto install_deps
    )
)

REM 创建虚拟环境
echo [信息] 正在创建虚拟环境...
python -m venv venv
if errorlevel 1 (
    echo [错误] 虚拟环境创建失败！
    pause
    exit /b 1
)
echo [成功] 虚拟环境创建完成
echo.

:install_deps
REM 激活虚拟环境
echo [信息] 正在激活虚拟环境...
call venv\Scripts\activate.bat

REM 升级 pip
echo [信息] 正在升级 pip...
python -m pip install --upgrade pip
echo.

REM 安装依赖
echo [信息] 正在安装项目依赖...
if exist "requirements.txt" (
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败！
        pause
        exit /b 1
    )
    echo [成功] 依赖安装完成
) else (
    echo [警告] 未找到 requirements.txt 文件！
)

echo.
echo ========================================
echo    安装完成！
echo ========================================
echo.
echo 使用方法:
echo   1. 双击 run.bat 启动应用
echo   2. 或在命令行中运行:
echo      venv\Scripts\activate.bat
echo      python src/main.py
echo.
pause
