#!/bin/bash

# Web版智能摄像头监控系统 - 启动脚本

echo "🎥 启动Web版智能摄像头监控系统"
echo "======================================"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行 ./setup.sh"
    exit 1
fi

# 激活虚拟环境
echo "🐍 激活虚拟环境..."
source venv/bin/activate

# 检查依赖
echo "📦 检查依赖包..."
python3 -c "
import sys
required_packages = ['flask', 'cv2', 'torch', 'transformers']
missing_packages = []

for package in required_packages:
    try:
        __import__(package)
        print(f'✅ {package}')
    except ImportError:
        missing_packages.append(package)
        print(f'❌ {package} (缺失)')

if missing_packages:
    print(f'\\n❌ 缺失依赖包: {missing_packages}')
    print('请运行: ./setup.sh')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

# 检查配置文件
if [ ! -f "config.py" ]; then
    echo "⚠️ 配置文件config.py不存在，使用默认配置"
fi

# 显示启动信息
echo ""
echo "🚀 启动系统..."
echo "📱 访问地址: http://localhost:5000"
echo "🛑 停止服务: Ctrl+C"
echo ""

# 启动应用
python3 app.py

echo ""
echo "👋 系统已停止"