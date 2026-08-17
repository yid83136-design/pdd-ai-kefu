@echo off
chcp 65001
echo ================================================
echo   安装 AI 客服脚本所需依赖
echo ================================================
echo.

echo 正在检查 Python 是否已安装...
python --version
if %errorlevel% neq 0 (
    echo.
    echo ❌ 未检测到 Python！
    echo 请先去 https://www.python.org/downloads/ 下载安装 Python
    echo 安装时记得勾选 "Add Python to PATH"
    pause
    exit
)

echo.
echo ✅ Python 已安装，开始安装依赖包...
echo.

pip install selenium requests webdriver-manager -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ================================================
echo   ✅ 安装完成！
echo   现在可以双击运行 "启动AI客服.bat" 了
echo ================================================
pause
