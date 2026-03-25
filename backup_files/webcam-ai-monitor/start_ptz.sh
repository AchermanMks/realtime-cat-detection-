#!/bin/bash

# Web版智能摄像头监控系统 + PTZ云台控制 - 启动脚本

echo "🎥🎮 启动Web版智能摄像头监控系统 + PTZ云台控制"
echo "======================================================"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行 ./setup.sh"
    exit 1
fi

# 激活虚拟环境
echo "🐍 激活虚拟环境..."
source venv/bin/activate

# 检查PTZ专用依赖
echo "📦 检查PTZ控制依赖包..."
python3 -c "
import sys
required_packages = ['flask', 'cv2', 'torch', 'transformers', 'requests', 'zeep', 'lxml']
missing_packages = []

for package in required_packages:
    try:
        if package == 'cv2':
            import cv2
            print(f'✅ opencv-python')
        else:
            __import__(package)
            print(f'✅ {package}')
    except ImportError:
        missing_packages.append(package)
        print(f'❌ {package} (缺失)')

if missing_packages:
    print(f'\\n❌ 缺失PTZ依赖包: {missing_packages}')
    print('请运行: pip install -r requirements_with_ptz.txt')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo ""
    echo "💡 安装PTZ依赖包："
    echo "pip install -r requirements_with_ptz.txt"
    exit 1
fi

# 检查配置文件
if [ ! -f "config_with_ptz.py" ]; then
    echo "⚠️ PTZ配置文件不存在，使用默认配置"
fi

# 显示PTZ功能说明
echo ""
echo "🎮 PTZ云台控制功能："
echo "   ✅ 支持海康威视、大华、ONVIF等协议"
echo "   ✅ Web界面云台控制面板"
echo "   ✅ 键盘快捷键控制 (方向键、+/-、空格)"
echo "   ✅ 预设位置管理"
echo "   ✅ 可调节速度控制"
echo ""

# 显示启动信息
echo "🚀 启动PTZ增强版系统..."
echo "📱 访问地址: http://localhost:5000"
echo "🎮 PTZ控制: 使用Web界面或键盘快捷键"
echo "⌨️ 键盘控制："
echo "   ↑↓←→  - 控制云台方向"
echo "   + -   - 控制变焦"
echo "   空格  - 停止移动"
echo "   1-5   - 预设位置"
echo "🛑 停止服务: Ctrl+C"
echo ""

# 启动PTZ版本应用
python3 app_with_ptz.py

echo ""
echo "👋 PTZ控制系统已停止"