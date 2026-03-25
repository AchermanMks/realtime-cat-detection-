#!/bin/bash

echo "🎥 RTSP AI监控系统启动脚本"
echo "================================"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查依赖是否安装
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 正在安装依赖..."
    pip3 install -r requirements.txt
fi

# 发现摄像头
echo "🔍 扫描网络摄像头..."
python3 quick_scan.py

echo ""
echo "🚀 启动选项:"
echo "1. 使用RTSP摄像头"
echo "2. 使用本地摄像头"
echo "3. 退出"

read -p "请选择 (1-3): " choice

case $choice in
    1)
        read -p "请输入RTSP URL: " rtsp_url
        echo "🌐 启动RTSP监控系统..."
        python3 integrated_camera_system.py --rtsp "$rtsp_url" --port 5000
        ;;
    2)
        read -p "请输入摄像头索引 (默认0): " camera_id
        camera_id=${camera_id:-0}
        echo "🌐 启动本地监控系统..."
        python3 integrated_camera_system.py --camera $camera_id --port 5000
        ;;
    3)
        echo "👋 再见!"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac