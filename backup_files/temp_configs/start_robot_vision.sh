#!/bin/bash

echo "🤖 机器人视觉识别系统启动脚本"
echo "=================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查必要的Python包
echo "📦 检查依赖包..."
python3 -c "import torch, cv2, transformers, requests; print('✅ 依赖包检查通过')" || {
    echo "❌ 缺少必要的Python包，请安装："
    echo "pip install torch torchvision transformers opencv-python requests qwen-vl-utils"
    exit 1
}

# 设置权限
chmod +x robot_vision_main.py

echo "🚀 启动选项:"
echo "1. 自动模式 (默认) - 自动视觉识别和跟踪"
echo "2. 交互模式 - 手动控制云台"
echo ""

read -p "选择模式 (1/2, 默认1): " mode

case $mode in
    2)
        echo "🎮 启动交互模式..."
        python3 robot_vision_main.py interactive
        ;;
    *)
        echo "🤖 启动自动模式..."
        python3 robot_vision_main.py
        ;;
esac

echo "✅ 系统已退出"