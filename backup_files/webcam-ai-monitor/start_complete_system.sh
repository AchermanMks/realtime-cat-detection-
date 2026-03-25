#!/bin/bash
# 智能摄像头监控与PTZ控制系统启动脚本

echo "🎥 智能摄像头监控与PTZ控制系统"
echo "================================="
echo ""

# 检查依赖
echo "🔍 检查系统依赖..."

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 未安装"
    exit 1
fi
echo "✅ Python 3: $(python3 --version)"

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请安装Node.js 16+"
    echo "   Ubuntu/Debian: sudo apt install nodejs npm"
    echo "   或访问: https://nodejs.org/"
    exit 1
fi
echo "✅ Node.js: $(node --version)"

# 检查Python依赖
echo ""
echo "🔍 检查Python依赖..."
if ! python3 -c "import flask, cv2, torch, transformers" 2>/dev/null; then
    echo "❌ Python依赖缺失，正在安装..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Python依赖安装失败"
        exit 1
    fi
fi
echo "✅ Python依赖完整"

echo ""
echo "📋 选择启动模式:"
echo "1) 完整系统 (视频监控 + PTZ控制)"
echo "2) 仅视频监控"
echo "3) 仅PTZ控制"
echo "4) 快速测试PTZ"
echo ""

read -p "请选择 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 启动完整系统..."
        echo ""

        # 启动Node.js PTZ代理
        echo "📡 启动PTZ代理服务器..."
        node ptz_proxy.js &
        PTZ_PROXY_PID=$!
        sleep 2

        # 检查代理是否启动成功
        if ps -p $PTZ_PROXY_PID > /dev/null; then
            echo "✅ PTZ代理启动成功 (PID: $PTZ_PROXY_PID)"
        else
            echo "❌ PTZ代理启动失败"
            exit 1
        fi

        # 启动视频监控
        echo "📺 启动视频监控..."
        python3 web_camera_stream.py --rtsp "rtsp://192.168.31.146:8554/unicast" &
        VIDEO_PID=$!
        sleep 3

        # 启动PTZ控制界面
        echo "🎮 启动PTZ控制界面..."
        python3 no_root_ptz_controller.py &
        PTZ_PID=$!
        sleep 2

        echo ""
        echo "✅ 系统启动完成!"
        echo ""
        echo "📱 访问地址:"
        echo "   视频监控: http://localhost:5000"
        echo "   PTZ控制: http://localhost:9999"
        echo ""
        echo "🛑 按 Ctrl+C 停止所有服务"
        echo ""

        # 等待用户中断
        trap 'echo ""; echo "🛑 正在停止服务..."; kill $PTZ_PROXY_PID $VIDEO_PID $PTZ_PID 2>/dev/null; echo "✅ 所有服务已停止"; exit 0' INT
        wait
        ;;

    2)
        echo ""
        echo "📺 仅启动视频监控..."
        echo ""
        echo "📱 访问地址: http://localhost:5000"
        echo ""
        python3 web_camera_stream.py --rtsp "rtsp://192.168.31.146:8554/unicast"
        ;;

    3)
        echo ""
        echo "🎮 仅启动PTZ控制..."
        echo ""

        # 启动Node.js PTZ代理
        echo "📡 启动PTZ代理服务器..."
        node ptz_proxy.js &
        PTZ_PROXY_PID=$!
        sleep 2

        # 检查代理是否启动成功
        if ps -p $PTZ_PROXY_PID > /dev/null; then
            echo "✅ PTZ代理启动成功"
        else
            echo "❌ PTZ代理启动失败"
            exit 1
        fi

        echo "📱 访问地址: http://localhost:9999"
        echo ""

        # 启动PTZ控制界面
        python3 no_root_ptz_controller.py

        # 清理
        kill $PTZ_PROXY_PID 2>/dev/null
        ;;

    4)
        echo ""
        echo "🎯 快速测试PTZ控制..."
        echo ""
        chmod +x simple_control.sh
        ./simple_control.sh
        ;;

    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac